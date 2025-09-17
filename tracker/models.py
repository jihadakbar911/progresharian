from django.db import models

# Create your models here.


class TaskCategory(models.TextChoices):
	ACADEMIC = 'ACADEMIC', 'Akademik'
	HEALTH = 'HEALTH', 'Kesehatan'
	DAILY = 'DAILY', 'Harian'


class DailyTask(models.Model):
	date = models.DateField(db_index=True)
	category = models.CharField(max_length=16, choices=TaskCategory.choices)
	title = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	is_completed = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-date', '-created_at']

	def __str__(self) -> str:
		return f"{self.date} - {self.get_category_display()}: {self.title}"


class Account(models.Model):
	name = models.CharField(max_length=100, unique=True)
	description = models.CharField(max_length=255, blank=True)
	initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return self.name

	@property
	def current_balance(self):
		income = self.transactions.filter(type=TransactionType.INCOME).aggregate(models.Sum('amount'))['amount__sum'] or 0
		expense = self.transactions.filter(type=TransactionType.EXPENSE).aggregate(models.Sum('amount'))['amount__sum'] or 0
		saving = self.savings.aggregate(models.Sum('amount'))['amount__sum'] or 0
		return self.initial_balance + income - expense - saving


class TransactionType(models.TextChoices):
	INCOME = 'INCOME', 'Pemasukan'
	EXPENSE = 'EXPENSE', 'Pengeluaran'


class Transaction(models.Model):
	account = models.ForeignKey(Account, related_name='transactions', on_delete=models.CASCADE)
	date = models.DateField(db_index=True)
	type = models.CharField(max_length=8, choices=TransactionType.choices)
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	category = models.CharField(max_length=100, blank=True)
	note = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-date', '-created_at']

	def __str__(self) -> str:
		return f"{self.date} {self.type} {self.amount} ({self.account.name})"


class SavingsGoal(models.Model):
	name = models.CharField(max_length=100, unique=True)
	target_amount = models.DecimalField(max_digits=12, decimal_places=2)
	description = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return self.name

	@property
	def saved_amount(self):
		return self.savings.aggregate(models.Sum('amount'))['amount__sum'] or 0

	@property
	def progress_percent(self):
		if self.target_amount and self.target_amount > 0:
			return float((self.saved_amount / self.target_amount) * 100)
		return 0.0


class Saving(models.Model):
	account = models.ForeignKey(Account, related_name='savings', on_delete=models.CASCADE)
	goal = models.ForeignKey(SavingsGoal, related_name='savings', on_delete=models.SET_NULL, null=True, blank=True)
	date = models.DateField(db_index=True)
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	goal_name = models.CharField(max_length=100, blank=True)
	note = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-date', '-created_at']

	def __str__(self) -> str:
		label = self.goal.name if self.goal else (self.goal_name or '-')
		return f"{self.date} NABUNG {self.amount} ({self.account.name}) [{label}]"


class UserPreferences(models.Model):
	preferred_academic_focus = models.CharField(max_length=200, blank=True, help_text='Misal: Python, Public Speaking')
	preferred_health_focus = models.CharField(max_length=200, blank=True, help_text='Misal: Jogging, Strength')
	daily_water_goal_glasses = models.PositiveIntegerField(default=8)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return 'Preferensi Pengguna'


class LearningLog(models.Model):
	date = models.DateField(db_index=True)
	topic = models.CharField(max_length=200)
	duration_minutes = models.PositiveIntegerField(default=0)
	key_takeaways = models.TextField(blank=True)
	source_url = models.URLField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-date', '-created_at']

	def __str__(self) -> str:
		return f"{self.date} - {self.topic} ({self.duration_minutes}m)"


class HealthLog(models.Model):
	date = models.DateField(db_index=True)
	activity = models.CharField(max_length=200)
	duration_or_sets = models.CharField(max_length=100, blank=True)
	note = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-date', '-created_at']

	def __str__(self) -> str:
		return f"{self.date} - {self.activity}"


class MindfulnessLog(models.Model):
	date = models.DateField(db_index=True)
	achievement = models.TextField(blank=True)
	challenge = models.TextField(blank=True)
	solution = models.TextField(blank=True)
	gratitude = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-date', '-created_at']

	def __str__(self) -> str:
		return f"{self.date} - Mindfulness"


class WaterIntake(models.Model):
	date = models.DateField(db_index=True)
	glasses = models.PositiveIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('date', 'created_at')
		ordering = ['-date', '-created_at']

	def __str__(self) -> str:
		return f"{self.date} - {self.glasses} gelas"
