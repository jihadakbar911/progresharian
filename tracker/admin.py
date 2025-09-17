from django.contrib import admin
from .models import DailyTask, Account, Transaction, Saving, SavingsGoal, UserPreferences, LearningLog, HealthLog, MindfulnessLog, WaterIntake


@admin.register(DailyTask)
class DailyTaskAdmin(admin.ModelAdmin):
	list_display = ('date', 'category', 'title', 'is_completed')
	list_filter = ('category', 'is_completed', 'date')
	search_fields = ('title', 'description')
	date_hierarchy = 'date'


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
	list_display = ('name', 'initial_balance', 'current_balance', 'created_at')
	search_fields = ('name',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
	list_display = ('date', 'account', 'type', 'amount', 'category')
	list_filter = ('type', 'account', 'date')
	search_fields = ('category', 'note')
	date_hierarchy = 'date'


@admin.register(Saving)
class SavingAdmin(admin.ModelAdmin):
	list_display = ('date', 'account', 'amount', 'goal', 'goal_name')
	list_filter = ('account', 'goal', 'date')
	search_fields = ('goal_name', 'note')
	date_hierarchy = 'date'


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
	list_display = ('name', 'target_amount', 'saved_amount', 'progress_percent', 'created_at')
	search_fields = ('name',)


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
	list_display = ('preferred_academic_focus', 'preferred_health_focus', 'daily_water_goal_glasses', 'created_at')


@admin.register(LearningLog)
class LearningLogAdmin(admin.ModelAdmin):
	list_display = ('date', 'topic', 'duration_minutes')
	search_fields = ('topic',)
	date_hierarchy = 'date'


@admin.register(HealthLog)
class HealthLogAdmin(admin.ModelAdmin):
	list_display = ('date', 'activity', 'duration_or_sets')
	search_fields = ('activity',)
	date_hierarchy = 'date'


@admin.register(MindfulnessLog)
class MindfulnessLogAdmin(admin.ModelAdmin):
	list_display = ('date',)
	date_hierarchy = 'date'


@admin.register(WaterIntake)
class WaterIntakeAdmin(admin.ModelAdmin):
	list_display = ('date', 'glasses')
	date_hierarchy = 'date'
