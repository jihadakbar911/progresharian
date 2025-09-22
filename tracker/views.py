from django.shortcuts import render, redirect
from django.views import View
from django.utils import timezone
from django.contrib import messages
from django.db.models import Sum, Count
from datetime import timedelta
from .models import DailyTask, TaskCategory, Account, Transaction, TransactionType, Saving, UserPreferences, LearningLog, HealthLog, MindfulnessLog, WaterIntake, SavingsGoal


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


class QuickAddSavingView(View):
	def post(self, request):
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
        account = _get_or_create_default_account()
        recent_transactions = Transaction.objects.select_related('account').order_by('-date', '-id')[:20]
        recent_savings = Saving.objects.select_related('account').order_by('-date', '-id')[:20]
        goals = SavingsGoal.objects.all().order_by('-created_at')
        context = {
            'today': today,
            'account': account,
            'current_balance': account.current_balance,
            'recent_transactions': recent_transactions,
            'recent_savings': recent_savings,
            'goals': goals,
        }
        return render(request, 'tracker/saldo.html', context)