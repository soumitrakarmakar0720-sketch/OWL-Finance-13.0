"""OWL FINANCE 7 Enterprise operations add-on. Additive tables only."""
from datetime import datetime, date
from decimal import Decimal
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session, Response
from sqlalchemy import func
import csv, io

_branch_models = None

def get_staff_branch_models():
    if _branch_models is None: raise RuntimeError("Enterprise models not installed")
    return _branch_models

def install(app, db, User, Application, Loan, Installment, Payment, Audit, DisbursementRecord):
    global _branch_models
    bp=Blueprint('enterprise',__name__,url_prefix='/admin/enterprise')
    class Branch(db.Model):
        __tablename__='enterprise_branch'
        id=db.Column(db.Integer,primary_key=True)
        code=db.Column(db.String(20),unique=True,nullable=False)
        name=db.Column(db.String(120),nullable=False)
        location=db.Column(db.String(200),nullable=False,default='')
        enabled=db.Column(db.Boolean,default=True,nullable=False)
    class StaffBranch(db.Model):
        __tablename__='enterprise_staff_branch'
        id=db.Column(db.Integer,primary_key=True)
        staff_id=db.Column(db.Integer,db.ForeignKey('user.id'),unique=True,nullable=False)
        branch_id=db.Column(db.Integer,db.ForeignKey('enterprise_branch.id'),nullable=False)
        assigned_at=db.Column(db.DateTime,default=datetime.utcnow,nullable=False)
    _branch_models=(Branch,StaffBranch)
    class Assignment(db.Model):
        __tablename__='enterprise_assignment'
        id=db.Column(db.Integer,primary_key=True)
        application_id=db.Column(db.Integer,db.ForeignKey('application.id'),unique=True,nullable=False)
        branch_id=db.Column(db.Integer,db.ForeignKey('enterprise_branch.id'),nullable=False)
        staff_id=db.Column(db.Integer,db.ForeignKey('user.id'))
        updated_at=db.Column(db.DateTime,default=datetime.utcnow)
    class Approval(db.Model):
        __tablename__='enterprise_approval'
        id=db.Column(db.Integer,primary_key=True)
        application_id=db.Column(db.Integer,db.ForeignKey('application.id'),nullable=False)
        stage=db.Column(db.String(30),nullable=False)
        decision=db.Column(db.String(20),nullable=False)
        reviewer_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
        notes=db.Column(db.Text,default='')
        created=db.Column(db.DateTime,default=datetime.utcnow)
    class Reconciliation(db.Model):
        __tablename__='enterprise_reconciliation'
        id=db.Column(db.Integer,primary_key=True)
        payment_id=db.Column(db.Integer,db.ForeignKey('payment.id'),unique=True,nullable=False)
        outcome=db.Column(db.String(30),nullable=False)
        reference=db.Column(db.String(120),nullable=False)
        notes=db.Column(db.Text,default='')
        actor_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
        created=db.Column(db.DateTime,default=datetime.utcnow)
    class Ticket(db.Model):
        __tablename__='enterprise_ticket'
        id=db.Column(db.Integer,primary_key=True)
        customer_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
        subject=db.Column(db.String(180),nullable=False)
        description=db.Column(db.Text,nullable=False)
        status=db.Column(db.String(20),default='open',nullable=False)
        owner_id=db.Column(db.Integer,db.ForeignKey('user.id'))
        resolution=db.Column(db.Text,default='')
        created=db.Column(db.DateTime,default=datetime.utcnow)
    class StaffPermission(db.Model):
        __tablename__='enterprise_staff_permission'
        id=db.Column(db.Integer,primary_key=True)
        staff_id=db.Column(db.Integer,db.ForeignKey('user.id'),unique=True,nullable=False)
        can_review=db.Column(db.Boolean,default=False,nullable=False)
        can_reconcile=db.Column(db.Boolean,default=False,nullable=False)
        can_support=db.Column(db.Boolean,default=True,nullable=False)
    def current():
        return db.session.get(User,session['uid']) if session.get('uid') else None
    def authorized(permission=None):
        def wrap(fn):
            @wraps(fn)
            def inner(*args,**kwargs):
                u=current()
                if not u: return redirect(url_for('login'))
                if u.role=='admin': return fn(*args,**kwargs)
                if u.role!='staff': abort(403)
                if permission:
                    p=StaffPermission.query.filter_by(staff_id=u.id).first()
                    if not p or not getattr(p,permission,False): abort(403)
                return fn(*args,**kwargs)
            return inner
        return wrap
    def log(action,subject,detail=''):
        db.session.add(Audit(actor_id=current().id,action=action,subject=subject,detail=detail[:1500]))
    @bp.get('/')
    @authorized()
    def index():
        today=date.today()
        overdue=db.session.query(func.count(func.distinct(Installment.loan_id))).join(Loan,Loan.id==Installment.loan_id).filter(Loan.status.in_(['active','demo_active']),Installment.due_date<today,Installment.paid<Installment.amount).scalar()
        return render_template('enterprise/index.html',counts={'applications':Application.query.count(),'active':Loan.query.filter(Loan.status.in_(['active','demo_active'])).count(),'overdue':overdue,'tickets':Ticket.query.filter(Ticket.status!='resolved').count(),'unreconciled':Payment.query.filter(Payment.status=='success').outerjoin(Reconciliation,Payment.id==Reconciliation.payment_id).filter(Reconciliation.id.is_(None)).count()},recent=Audit.query.order_by(Audit.id.desc()).limit(12).all())
    @bp.route('/branches',methods=['GET','POST'])
    @authorized()
    def branches():
        if request.method=='POST':
            if current().role!='admin': abort(403)
            code=request.form.get('code','').strip().upper()[:20]
            name=request.form.get('name','').strip()[:120]
            if not code.isalnum() or not name: abort(400,'Valid branch code and name required')
            if Branch.query.filter_by(code=code).first(): abort(409,'Branch code already exists')
            db.session.add(Branch(code=code,name=name,location=request.form.get('location','').strip()[:200]));log('branch_created',code);db.session.commit()
            return redirect(url_for('.branches'))
        return render_template('enterprise/branches.html',branches=Branch.query.order_by(Branch.name).all())
    @bp.route('/staff',methods=['GET','POST'])
    @authorized()
    def staff_branches():
        if current().role!='admin': abort(403)
        if request.method=='POST':
            try: sid=int(request.form.get('staff_id',''));bid=int(request.form.get('branch_id',''))
            except ValueError: abort(400)
            staff=db.session.get(User,sid);branch=db.session.get(Branch,bid)
            if not staff or staff.role!='staff' or not branch or not branch.enabled: abort(400)
            # Do not silently leave applications assigned to a staff member in another branch.
            if Assignment.query.filter(Assignment.staff_id==sid,Assignment.branch_id!=bid).first():
                flash('Reassign existing applications before moving this employee to another branch.')
                return redirect(url_for('.staff_branches'))
            row=StaffBranch.query.filter_by(staff_id=sid).first()
            if row is None: row=StaffBranch(staff_id=sid,branch_id=bid);db.session.add(row)
            else: row.branch_id=bid;row.assigned_at=datetime.utcnow()
            log('staff_branch_assigned',f'staff:{sid}',f'branch:{bid}')
            db.session.commit();flash('Staff branch updated.')
            return redirect(url_for('.staff_branches'))
        rows=StaffBranch.query.all()
        return render_template('enterprise/staff_branches.html',staff=User.query.filter_by(role='staff').order_by(User.name).all(),branches=Branch.query.filter_by(enabled=True).order_by(Branch.name).all(),memberships={r.staff_id:r.branch_id for r in rows},branch_names={b.id:b.name for b in Branch.query.all()})
    @bp.route('/assignments',methods=['GET','POST'])
    @authorized()
    def assignments():
        if request.method=='POST':
            if current().role!='admin': abort(403)
            aid=int(request.form.get('application_id',0));bid=int(request.form.get('branch_id',0));sid=int(request.form.get('staff_id',0) or 0)
            a=db.session.get(Application,aid);b=db.session.get(Branch,bid);staff=db.session.get(User,sid) if sid else None
            if not a or not b or not b.enabled or (sid and (not staff or staff.role!='staff')): abort(400)
            if sid and not StaffBranch.query.filter_by(staff_id=sid,branch_id=bid).first(): abort(400,'Staff member must belong to the selected branch')
            row=Assignment.query.filter_by(application_id=aid).first()
            if not row: row=Assignment(application_id=aid,branch_id=bid);db.session.add(row)
            row.branch_id=bid;row.staff_id=sid or None;row.updated_at=datetime.utcnow()
            log('application_assigned',f'application:{aid}',f'branch:{bid} staff:{sid}');db.session.commit()
            return redirect(url_for('.assignments'))
        return render_template('enterprise/assignments.html',rows=Assignment.query.order_by(Assignment.updated_at.desc()).all(),branches=Branch.query.filter_by(enabled=True).all(),staff=User.query.filter_by(role='staff').all(),staff_branches={r.staff_id:r.branch_id for r in StaffBranch.query.all()},applications=Application.query.order_by(Application.id.desc()).limit(300).all())
    @bp.route('/approvals',methods=['GET','POST'])
    @authorized('can_review')
    def approvals():
        if request.method=='POST':
            aid=int(request.form.get('application_id',0));a=db.session.get(Application,aid)
            stage=request.form.get('stage');decision=request.form.get('decision')
            if not a or stage not in ('kyc_review','credit_review','disbursement_review') or decision not in ('recommend','return','reject'):abort(400)
            db.session.add(Approval(application_id=aid,stage=stage,decision=decision,reviewer_id=current().id,notes=request.form.get('notes','')[:1000]));log('review_recorded',f'application:{aid}',f'{stage}:{decision}');db.session.commit()
            flash('Review recorded. This does not approve KYC, disburse funds or change the loan ledger.')
            return redirect(url_for('.approvals'))
        return render_template('enterprise/approvals.html',rows=Approval.query.order_by(Approval.id.desc()).limit(150).all(),applications=Application.query.order_by(Application.id.desc()).limit(300).all())
    @bp.route('/reconciliation',methods=['GET','POST'])
    @authorized('can_reconcile')
    def reconciliation():
        if request.method=='POST':
            pid=int(request.form.get('payment_id',0));p=db.session.get(Payment,pid)
            outcome=request.form.get('outcome');reference=request.form.get('reference','').strip()[:120]
            if not p or outcome not in ('matched','investigate') or len(reference)<5:abort(400)
            if outcome=='matched' and p.status!='success':abort(409,'Only verified successful gateway payments may be matched')
            r=Reconciliation.query.filter_by(payment_id=pid).first()
            if r: abort(409,'Reconciliation already recorded; escalate correction to audit review')
            db.session.add(Reconciliation(payment_id=pid,outcome=outcome,reference=reference,notes=request.form.get('notes','')[:1000],actor_id=current().id));log('payment_reconciled',f'payment:{pid}',outcome);db.session.commit()
            return redirect(url_for('.reconciliation'))
        payments=Payment.query.order_by(Payment.id.desc()).limit(300).all()
        records={r.payment_id:r for r in Reconciliation.query.filter(Reconciliation.payment_id.in_([p.id for p in payments])).all()} if payments else {}
        return render_template('enterprise/reconciliation.html',payments=payments,records=records)
    @bp.route('/tickets',methods=['GET','POST'])
    @authorized('can_support')
    def tickets():
        if request.method=='POST':
            cid=int(request.form.get('customer_id',0));u=db.session.get(User,cid)
            if not u or u.role!='customer':abort(400)
            subject=request.form.get('subject','').strip()[:180];description=request.form.get('description','').strip()[:3000]
            if len(subject)<4 or len(description)<8:abort(400)
            db.session.add(Ticket(customer_id=cid,subject=subject,description=description));log('ticket_created',f'customer:{cid}');db.session.commit()
            return redirect(url_for('.tickets'))
        return render_template('enterprise/tickets.html',tickets=Ticket.query.order_by(Ticket.id.desc()).limit(200).all(),customers=User.query.filter_by(role='customer').all())
    @bp.post('/tickets/<int:tid>/resolve')
    @authorized('can_support')
    def resolve(tid):
        t=db.get_or_404(Ticket,tid);note=request.form.get('resolution','').strip()
        if len(note)<8:abort(400)
        t.status='resolved';t.resolution=note[:2000];t.owner_id=current().id;log('ticket_resolved',f'ticket:{tid}');db.session.commit()
        return redirect(url_for('.tickets'))
    @bp.route('/permissions',methods=['GET','POST'])
    @authorized()
    def permissions():
        if current().role!='admin':abort(403)
        if request.method=='POST':
            sid=int(request.form.get('staff_id',0));u=db.session.get(User,sid)
            if not u or u.role!='staff':abort(400)
            p=StaffPermission.query.filter_by(staff_id=sid).first()
            if not p:p=StaffPermission(staff_id=sid);db.session.add(p)
            p.can_review='can_review' in request.form;p.can_reconcile='can_reconcile' in request.form;p.can_support='can_support' in request.form
            log('staff_permissions_updated',f'user:{sid}',f'review:{p.can_review},reconcile:{p.can_reconcile},support:{p.can_support}');db.session.commit()
            return redirect(url_for('.permissions'))
        staff=User.query.filter_by(role='staff').all();permissions={p.staff_id:p for p in StaffPermission.query.all()}
        return render_template('enterprise/permissions.html',staff=staff,permissions=permissions)
    @bp.get('/overdue')
    @authorized()
    def overdue():
        rows=Installment.query.join(Loan,Installment.loan_id==Loan.id).filter(Loan.status.in_(['active','demo_active']),Installment.due_date<date.today(),Installment.paid<Installment.amount).order_by(Installment.due_date).limit(300).all()
        return render_template('enterprise/overdue.html',rows=rows)
    @bp.get('/audit.csv')
    @authorized()
    def audit_csv():
        if current().role!='admin':abort(403)
        out=io.StringIO();w=csv.writer(out);w.writerow(['id','time_utc','actor_id','action','subject','detail'])
        for a in Audit.query.order_by(Audit.id.desc()).limit(10000):w.writerow([a.id,a.created.isoformat() if a.created else '',a.actor_id,a.action,a.subject,a.detail])
        log('audit_export','enterprise:audit');db.session.commit()
        return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=owl-finance-audit.csv','Cache-Control':'no-store'})
    app.register_blueprint(bp)
