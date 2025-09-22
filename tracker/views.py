from django.shortcuts import render, redirect
from django.http import HttpResponse
import csv
from django.views import View
from django.utils import timezone
from django.contrib import messages
from django.db.models import Sum, Count
from datetime import timedelta
from .models import DailyTask, TaskCategory, Account, Transaction, TransactionType, Saving, UserPreferences, LearningLog, HealthLog, MindfulnessLog, WaterIntake, SavingsGoal, RecurringTransaction, RecurringTask, RecurrenceFrequency


def _get_or_create_default_account() -> Account:
	account, _ = Account.objects.get_or_create(name='Dompet Utama', defaults={'initial_balance': 0})
	return account


def _get_or_create_preferences() -> UserPreferences:
	prefs, _ = UserPreferences.objects.get_or_create(id=1)
	return prefs


def _quote_of_the_day(date):
	quotes = [
		"Langkah kecil hari ini adalah kemenangan besar esok hari.",
		"Konsistensi mengalahkan intensitas.",
		"Belajar itu investasi terbaik untuk diri sendiri.",
		"Tubuh sehat, pikiran tajam.",
		"Progres lebih penting daripada kesempurnaan.",
	]
	return quotes[date.toordinal() % len(quotes)]


def _suggest_tasks_for_today(prefs: UserPreferences, today):
	# Akademik
	if not DailyTask.objects.filter(date=today, category=TaskCategory.ACADEMIC).exists():
		focus = prefs.preferred_academic_focus or 'topik favoritmu'
		DailyTask.objects.create(
			date=today,
			category=TaskCategory.ACADEMIC,
			title=f"Belajar: {focus} (45 menit)",
			description=f"Fokus pada 1 sub-topik {focus}. Catat 3 poin penting.",
		)
	# Kesehatan
	if not DailyTask.objects.filter(date=today, category=TaskCategory.HEALTH).exists():
		health = prefs.preferred_health_focus or 'jalan cepat'
		DailyTask.objects.create(
			date=today,
			category=TaskCategory.HEALTH,
			title=f"Olahraga: {health}",
			description="Minimal 25-30 menit. Lakukan pemanasan & pendinginan.",
		)
	# Harian/Mindfulness
	if not DailyTask.objects.filter(date=today, category=TaskCategory.DAILY).exists():
		DailyTask.objects.create(
			date=today,
			category=TaskCategory.DAILY,
			title="Mindfulness: Tulis 3 hal yang disyukuri",
			description="Luangkan 5 menit untuk refleksi dan syukur.",
		)


class DashboardView(View):
	def get(self, request):
		today = timezone.localdate()
		week_start = today - timedelta(days=today.weekday())
		week_end = week_start + timedelta(days=6)

		tasks_today = DailyTask.objects.filter(date=today).order_by('category', 'created_at')
		# Fokus hari ini: pick satu per kategori jika ada
		focus = {
			'academic': tasks_today.filter(category=TaskCategory.ACADEMIC).first(),
			'health': tasks_today.filter(category=TaskCategory.HEALTH).first(),
			'daily': tasks_today.filter(category=TaskCategory.DAILY).first(),
		}

		account = _get_or_create_default_account()
		recent_transactions = Transaction.objects.select_related('account').order_by('-date', '-id')[:5]
		recent_savings = Saving.objects.select_related('account').order_by('-date', '-id')[:5]

		# Weekly progress chart data: completed counts per day
		weekly_counts = []
		for i in range(7):
			day = week_start + timedelta(days=i)
			completed = DailyTask.objects.filter(date=day, is_completed=True).count()
			total = DailyTask.objects.filter(date=day).count()
			weekly_counts.append({'date': day.isoformat(), 'completed': completed, 'total': total})

		# Water tracker
		prefs = _get_or_create_preferences()
		water_today, _ = WaterIntake.objects.get_or_create(date=today, defaults={'glasses': 0})

		# Savings goals
		goals = SavingsGoal.objects.all().order_by('-created_at')[:5]

		# Recent logs
		learning_recent = LearningLog.objects.order_by('-date', '-id')[:5]
		health_recent = HealthLog.objects.order_by('-date', '-id')[:5]
		mind_recent = MindfulnessLog.objects.order_by('-date', '-id')[:5]

		# Streaks up to today
		def _calc_streak(model_cls):
			streak = 0
			day = today
			while True:
				exists = model_cls.objects.filter(date=day).exists()
				if not exists:
					break
				streak += 1
				day = day - timedelta(days=1)
			return streak

		learning_streak = _calc_streak(LearningLog)
		health_streak = _calc_streak(HealthLog)

		context = {
			'today': today,
			'tasks': tasks_today,
			'categories': TaskCategory.choices,
			'account': account,
			'current_balance': account.current_balance,
			'recent_transactions': recent_transactions,
			'recent_savings': recent_savings,
			'focus': focus,
			'quote': _quote_of_the_day(today),
			'weekly_counts': weekly_counts,
			'prefs': prefs,
			'water_today': water_today,
			'goals': goals,
			'learning_recent': learning_recent,
			'health_recent': health_recent,
			'mind_recent': mind_recent,
			'learning_streak': learning_streak,
			'health_streak': health_streak,
		}
		return render(request, 'tracker/dashboard.html', context)


class QuickAddTaskView(View):
	def post(self, request):
		date_str = request.POST.get('date')
		category = request.POST.get('category')
		title = request.POST.get('title')
		description = request.POST.get('description', '')
		if not (date_str and category and title):
			messages.error(request, 'Tanggal, kategori, dan judul wajib diisi')
			return redirect('tracker:dashboard')
		DailyTask.objects.create(date=date_str, category=category, title=title, description=description)
		messages.success(request, 'Tugas ditambahkan')
		return redirect('tracker:dashboard')


class ToggleTaskDoneView(View):
	def post(self, request, task_id: int):
		task = DailyTask.objects.get(id=task_id)
		task.is_completed = not task.is_completed
		task.save(update_fields=['is_completed'])
		return redirect('tracker:dashboard')


class QuickAddTransactionView(View):
	def post(self, request):
		account_id = request.POST.get('account_id')
		if account_id:
			account = Account.objects.filter(id=account_id).first() or _get_or_create_default_account()
		else:
			account = _get_or_create_default_account()
		date_str = request.POST.get('date')
		type_ = request.POST.get('type')
		amount = request.POST.get('amount')
		category = request.POST.get('category', '')
		note = request.POST.get('note', '')
		if not (date_str and type_ and amount):
			messages.error(request, 'Tanggal, jenis, dan nominal wajib diisi')
			return redirect('tracker:dashboard')
		Transaction.objects.create(
			account=account,
			date=date_str,
			type=type_,
			amount=amount,
			category=category,
			note=note,
		)
		messages.success(request, 'Transaksi dicatat')
		return redirect('tracker:dashboard')


class DeleteTransactionView(View):
	def post(self, request, transaction_id: int):
		try:
			tr = Transaction.objects.get(id=transaction_id)
			tr.delete()
			messages.success(request, 'Transaksi dihapus')
		except Transaction.DoesNotExist:
			messages.error(request, 'Transaksi tidak ditemukan')
		return redirect('tracker:dashboard')


class EditTransactionView(View):
	def post(self, request, transaction_id: int):
		tr = Transaction.objects.filter(id=transaction_id).first()
		if not tr:
			messages.error(request, 'Transaksi tidak ditemukan')
			return redirect('tracker:saldo')
		date_str = request.POST.get('date') or tr.date
		type_ = request.POST.get('type') or tr.type
		amount = request.POST.get('amount') or tr.amount
		category = request.POST.get('category', tr.category)
		note = request.POST.get('note', tr.note)
		tr.date = date_str
		tr.type = type_
		tr.amount = amount
		tr.category = category
		tr.note = note
		tr.save()
		messages.success(request, 'Transaksi diperbarui')
		return redirect('tracker:saldo')


class QuickAddSavingView(View):
	def post(self, request):
		account_id = request.POST.get('account_id')
		if account_id:
			account = Account.objects.filter(id=account_id).first() or _get_or_create_default_account()
		else:
			account = _get_or_create_default_account()
		date_str = request.POST.get('date')
		amount = request.POST.get('amount')
		goal_id = request.POST.get('goal_id')
		goal_name = request.POST.get('goal_name', '')
		note = request.POST.get('note', '')
		if not (date_str and amount):
			messages.error(request, 'Tanggal dan nominal nabung wajib diisi')
			return redirect('tracker:dashboard')
		goal = SavingsGoal.objects.filter(id=goal_id).first() if goal_id else None
		Saving.objects.create(
			account=account,
			date=date_str,
			amount=amount,
			goal=goal,
			goal_name=goal_name,
			note=note,
		)
		messages.success(request, 'Tabungan ditambahkan')
		return redirect('tracker:dashboard')


class EditSavingView(View):
	def post(self, request, saving_id: int):
		sv = Saving.objects.filter(id=saving_id).first()
		if not sv:
			messages.error(request, 'Tabungan tidak ditemukan')
			return redirect('tracker:saldo')
		date_str = request.POST.get('date') or sv.date
		amount = request.POST.get('amount') or sv.amount
		goal_name = request.POST.get('goal_name', sv.goal_name)
		note = request.POST.get('note', sv.note)
		goal_id = request.POST.get('goal_id')
		goal = SavingsGoal.objects.filter(id=goal_id).first() if goal_id else None
		sv.date = date_str
		sv.amount = amount
		sv.goal = goal
		sv.goal_name = goal_name
		sv.note = note
		sv.save()
		messages.success(request, 'Tabungan diperbarui')
		return redirect('tracker:saldo')


class WaterAddView(View):
	def post(self, request):
		today = timezone.localdate()
		water, _ = WaterIntake.objects.get_or_create(date=today, defaults={'glasses': 0})
		water.glasses += 1
		water.save(update_fields=['glasses'])
		return redirect('tracker:dashboard')


class SuggestTasksAIView(View):
	def post(self, request):
		today = timezone.localdate()
		prefs = _get_or_create_preferences()
		_suggest_tasks_for_today(prefs, today)
		messages.success(request, 'Saran tugas untuk hari ini telah ditambahkan.')
		return redirect('tracker:dashboard')


class AddLearningLogView(View):
	def post(self, request):
		date = request.POST.get('date')
		topic = request.POST.get('topic')
		duration = int(request.POST.get('duration') or 0)
		key = request.POST.get('key_takeaways', '')
		src = request.POST.get('source_url', '')
		if not (date and topic):
			messages.error(request, 'Tanggal dan topik wajib diisi')
			return redirect('tracker:dashboard')
		LearningLog.objects.create(date=date, topic=topic, duration_minutes=duration, key_takeaways=key, source_url=src)
		messages.success(request, 'Log pembelajaran ditambahkan')
		return redirect('tracker:dashboard')


class AddHealthLogView(View):
	def post(self, request):
		date = request.POST.get('date')
		activity = request.POST.get('activity')
		duration_sets = request.POST.get('duration_or_sets', '')
		note = request.POST.get('note', '')
		if not (date and activity):
			messages.error(request, 'Tanggal dan jenis olahraga wajib diisi')
			return redirect('tracker:dashboard')
		HealthLog.objects.create(date=date, activity=activity, duration_or_sets=duration_sets, note=note)
		messages.success(request, 'Log kesehatan ditambahkan')
		return redirect('tracker:dashboard')


class AddMindfulnessLogView(View):
	def post(self, request):
		date = request.POST.get('date')
		achievement = request.POST.get('achievement', '')
		challenge = request.POST.get('challenge', '')
		solution = request.POST.get('solution', '')
		gratitude = request.POST.get('gratitude', '')
		if not date:
			messages.error(request, 'Tanggal wajib diisi')
			return redirect('tracker:dashboard')
		MindfulnessLog.objects.create(date=date, achievement=achievement, challenge=challenge, solution=solution, gratitude=gratitude)
		messages.success(request, 'Jurnal harian ditambahkan')
		return redirect('tracker:dashboard')


class ReportsView(View):
	def get(self, request):
		today = timezone.localdate()
		month_start = today.replace(day=1)
		transactions = Transaction.objects.filter(date__gte=month_start, date__lte=today)
		by_category = transactions.filter(type=TransactionType.EXPENSE).values('category').annotate(total=Sum('amount')).order_by('-total')
		income_total = transactions.filter(type=TransactionType.INCOME).aggregate(Sum('amount'))['amount__sum'] or 0
		expense_total = transactions.filter(type=TransactionType.EXPENSE).aggregate(Sum('amount'))['amount__sum'] or 0
		learning_minutes = LearningLog.objects.filter(date__gte=month_start, date__lte=today).aggregate(Sum('duration_minutes'))['duration_minutes__sum'] or 0
		health_count = HealthLog.objects.filter(date__gte=month_start, date__lte=today).count()
		context = {
			'today': today,
			'month_start': month_start,
			'by_category': list(by_category),
			'income_total': income_total,
			'expense_total': expense_total,
			'learning_minutes': learning_minutes,
			'health_count': health_count,
		}
		return render(request, 'tracker/reports.html', context)


class SaldoView(View):
	def get(self, request):
		today = timezone.localdate()
		# Accounts
		accounts = Account.objects.all().order_by('name')
		selected_id = request.GET.get('account_id')
		account = None
		if selected_id:
			account = Account.objects.filter(id=selected_id).first()
		if not account:
			account = _get_or_create_default_account()
		# Filters
		start = request.GET.get('start')
		end = request.GET.get('end')
		q = request.GET.get('q', '').strip()
		ttype = request.GET.get('type', '').strip()  # INCOME / EXPENSE

		tr_qs = Transaction.objects.select_related('account').order_by('-date', '-id')
		if start:
			tr_qs = tr_qs.filter(date__gte=start)
		if end:
			tr_qs = tr_qs.filter(date__lte=end)
		if ttype in (TransactionType.INCOME, TransactionType.EXPENSE):
			tr_qs = tr_qs.filter(type=ttype)
		if q:
			from django.db.models import Q
			tr_qs = tr_qs.filter(Q(category__icontains=q) | Q(note__icontains=q))
		recent_transactions = tr_qs[:50]

		sv_qs = Saving.objects.select_related('account').order_by('-date', '-id')
		if start:
			sv_qs = sv_qs.filter(date__gte=start)
		if end:
			sv_qs = sv_qs.filter(date__lte=end)
		if q:
			from django.db.models import Q
			sv_qs = sv_qs.filter(Q(goal_name__icontains=q) | Q(note__icontains=q))
		recent_savings = sv_qs[:50]
		recurring_tr = RecurringTransaction.objects.filter(account=account).order_by('next_date', 'id')
		goals = SavingsGoal.objects.all().order_by('-created_at')
		context = {
			'today': today,
			'account': account,
			'current_balance': account.current_balance,
			'recent_transactions': recent_transactions,
			'recent_savings': recent_savings,
			'recurring_transactions': recurring_tr,
			'goals': goals,
			'accounts': accounts,
			'selected_account_id': str(account.id),
			'filters': {
				'start': start or '',
				'end': end or '',
				'q': q,
				'type': ttype,
			}
		}
		return render(request, 'tracker/saldo.html', context)


class CreateAccountView(View):
    def post(self, request):
        name = request.POST.get('name')
        initial_balance = request.POST.get('initial_balance') or '0'
        description = request.POST.get('description', '')
        if not name:
            messages.error(request, 'Nama akun wajib diisi')
            return redirect('tracker:saldo')
        try:
            initial = float(initial_balance)
        except ValueError:
            messages.error(request, 'Saldo awal tidak valid')
            return redirect('tracker:saldo')
        acc, created = Account.objects.get_or_create(name=name, defaults={'initial_balance': initial, 'description': description})
        if not created:
            messages.info(request, 'Akun sudah ada, gunakan yang lama')
        else:
            messages.success(request, 'Akun dibuat')
        return redirect(f"/saldo?account_id={acc.id}")


def _advance_date(date_obj, frequency: str):
	if frequency == RecurrenceFrequency.DAILY:
		return date_obj + timedelta(days=1)
	if frequency == RecurrenceFrequency.WEEKLY:
		return date_obj + timedelta(weeks=1)
	# MONTHLY default: naive month add
	month = date_obj.month + 1
	year = date_obj.year + (month - 1) // 12
	month = (month - 1) % 12 + 1
	day = min(date_obj.day, 28)
	return date_obj.replace(year=year, month=month, day=day)


class GenerateRecurringFinanceView(View):
	def post(self, request):
		today = timezone.localdate()
		generated = 0
		recurs = RecurringTransaction.objects.filter(is_active=True, next_date__lte=today)
		for r in recurs:
			Transaction.objects.create(
				account=r.account,
				date=r.next_date,
				type=r.type,
				amount=r.amount,
				category=r.category,
				note=r.note,
			)
			generated += 1
			r.next_date = _advance_date(r.next_date, r.frequency)
			r.save(update_fields=['next_date'])
		messages.success(request, f'Recurring transaksi digenerate: {generated}')
		return redirect('tracker:saldo')


class RecurringTransactionCreateView(View):
	def post(self, request):
		account_id = request.POST.get('account_id')
		account = Account.objects.filter(id=account_id).first() or _get_or_create_default_account()
		type_ = request.POST.get('type')
		amount = request.POST.get('amount')
		category = request.POST.get('category', '')
		note = request.POST.get('note', '')
		frequency = request.POST.get('frequency') or RecurrenceFrequency.MONTHLY
		next_date = request.POST.get('next_date')
		if not (type_ and amount and next_date):
			messages.error(request, 'Jenis, nominal, dan tanggal berikutnya wajib diisi')
			return redirect(f"/saldo?account_id={account.id}")
		RecurringTransaction.objects.create(account=account, type=type_, amount=amount, category=category, note=note, frequency=frequency, next_date=next_date)
		messages.success(request, 'Template transaksi berulang dibuat')
		return redirect(f"/saldo?account_id={account.id}")


class RecurringTransactionEditView(View):
	def post(self, request, rt_id: int):
		rt = RecurringTransaction.objects.filter(id=rt_id).first()
		if not rt:
			messages.error(request, 'Template tidak ditemukan')
			return redirect('tracker:saldo')
		rt.type = request.POST.get('type', rt.type)
		rt.amount = request.POST.get('amount', rt.amount)
		rt.category = request.POST.get('category', rt.category)
		rt.note = request.POST.get('note', rt.note)
		rt.frequency = request.POST.get('frequency', rt.frequency)
		rt.next_date = request.POST.get('next_date', rt.next_date)
		rt.is_active = (request.POST.get('is_active') == 'on') if 'is_active' in request.POST else rt.is_active
		rt.save()
		messages.success(request, 'Template transaksi berulang diperbarui')
		return redirect(f"/saldo?account_id={rt.account.id}")


class RecurringTransactionDeleteView(View):
	def post(self, request, rt_id: int):
		rt = RecurringTransaction.objects.filter(id=rt_id).first()
		if not rt:
			messages.error(request, 'Template tidak ditemukan')
			return redirect('tracker:saldo')
		acc_id = rt.account.id
		rt.delete()
		messages.success(request, 'Template transaksi berulang dihapus')
		return redirect(f"/saldo?account_id={acc_id}")


class GenerateRecurringTasksView(View):
	def post(self, request):
		today = timezone.localdate()
		generated = 0
		recurs = RecurringTask.objects.filter(is_active=True, next_date__lte=today)
		for r in recurs:
			DailyTask.objects.create(
				date=r.next_date,
				category=r.category,
				title=r.title,
				description=r.description,
			)
			generated += 1
			r.next_date = _advance_date(r.next_date, r.frequency)
			r.save(update_fields=['next_date'])
		messages.success(request, f'Recurring tugas digenerate: {generated}')
		return redirect('tracker:dashboard')


class ExportTransactionsCSVView(View):
    def get(self, request):
        account_id = request.GET.get('account_id')
        qs = Transaction.objects.select_related('account').order_by('date', 'id')
        if account_id:
            qs = qs.filter(account_id=account_id)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        writer = csv.writer(response)
        writer.writerow(['date', 'account', 'type', 'amount', 'category', 'note'])
        for tr in qs:
            writer.writerow([tr.date.isoformat(), tr.account.name, tr.type, tr.amount, tr.category, tr.note])
        return response


class ExportSavingsCSVView(View):
    def get(self, request):
        account_id = request.GET.get('account_id')
        qs = Saving.objects.select_related('account', 'goal').order_by('date', 'id')
        if account_id:
            qs = qs.filter(account_id=account_id)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="savings.csv"'
        writer = csv.writer(response)
        writer.writerow(['date', 'account', 'amount', 'goal', 'goal_name', 'note'])
        for sv in qs:
            writer.writerow([sv.date.isoformat(), sv.account.name, sv.amount, sv.goal.name if sv.goal else '', sv.goal_name, sv.note])
        return response


class ImportTransactionsCSVView(View):
    def post(self, request):
        file = request.FILES.get('file')
        account_id = request.POST.get('account_id')
        account = Account.objects.filter(id=account_id).first() if account_id else _get_or_create_default_account()
        if not file:
            messages.error(request, 'File CSV tidak ditemukan')
            return redirect('tracker:saldo')
        decoded = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded)
        created = 0
        for row in reader:
            try:
                date = row.get('date')
                type_ = row.get('type')
                amount = row.get('amount')
                category = row.get('category', '')
                note = row.get('note', '')
                if date and type_ and amount:
                    Transaction.objects.create(account=account, date=date, type=type_, amount=amount, category=category, note=note)
                    created += 1
            except Exception:
                continue
        messages.success(request, f'Impor transaksi: {created} baris ditambahkan')
        return redirect(f"/saldo?account_id={account.id}")


class ImportSavingsCSVView(View):
    def post(self, request):
        file = request.FILES.get('file')
        account_id = request.POST.get('account_id')
        account = Account.objects.filter(id=account_id).first() if account_id else _get_or_create_default_account()
        if not file:
            messages.error(request, 'File CSV tidak ditemukan')
            return redirect('tracker:saldo')
        decoded = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded)
        created = 0
        for row in reader:
            try:
                date = row.get('date')
                amount = row.get('amount')
                goal_name = row.get('goal_name', '')
                note = row.get('note', '')
                goal_title = row.get('goal', '')
                goal = SavingsGoal.objects.filter(name=goal_title).first() if goal_title else None
                if date and amount:
                    Saving.objects.create(account=account, date=date, amount=amount, goal=goal, goal_name=goal_name, note=note)
                    created += 1
            except Exception:
                continue
        messages.success(request, f'Impor tabungan: {created} baris ditambahkan')
        return redirect(f"/saldo?account_id={account.id}")