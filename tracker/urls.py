from django.urls import path
from .views import DashboardView, QuickAddTaskView, ToggleTaskDoneView, QuickAddTransactionView, QuickAddSavingView, WaterAddView, ReportsView, SuggestTasksAIView, AddLearningLogView, AddHealthLogView, AddMindfulnessLogView, DeleteTransactionView, SaldoView, CreateAccountView, EditTransactionView, EditSavingView, ExportTransactionsCSVView, ExportSavingsCSVView, ImportTransactionsCSVView, ImportSavingsCSVView, GenerateRecurringFinanceView, GenerateRecurringTasksView, RecurringTransactionCreateView, RecurringTransactionEditView, RecurringTransactionDeleteView

app_name = 'tracker'

urlpatterns = [
	path('', DashboardView.as_view(), name='dashboard'),
    path('saldo', SaldoView.as_view(), name='saldo'),
    path('finance/account/create', CreateAccountView.as_view(), name='account-create'),
	path('tasks/add', QuickAddTaskView.as_view(), name='task-add'),
	path('tasks/<int:task_id>/toggle', ToggleTaskDoneView.as_view(), name='task-toggle'),
	path('tasks/suggest-ai', SuggestTasksAIView.as_view(), name='task-suggest-ai'),
	path('logs/learning/add', AddLearningLogView.as_view(), name='learning-add'),
	path('logs/health/add', AddHealthLogView.as_view(), name='health-add'),
	path('logs/mindfulness/add', AddMindfulnessLogView.as_view(), name='mindfulness-add'),
	path('finance/transaction/add', QuickAddTransactionView.as_view(), name='transaction-add'),
	path('finance/transaction/<int:transaction_id>/delete', DeleteTransactionView.as_view(), name='transaction-delete'),
    path('finance/transaction/<int:transaction_id>/edit', EditTransactionView.as_view(), name='transaction-edit'),
    path('finance/transaction/export.csv', ExportTransactionsCSVView.as_view(), name='transaction-export'),
    path('finance/transaction/import', ImportTransactionsCSVView.as_view(), name='transaction-import'),
	path('finance/saving/add', QuickAddSavingView.as_view(), name='saving-add'),
    path('finance/saving/<int:saving_id>/edit', EditSavingView.as_view(), name='saving-edit'),
    path('finance/saving/export.csv', ExportSavingsCSVView.as_view(), name='saving-export'),
    path('finance/saving/import', ImportSavingsCSVView.as_view(), name='saving-import'),
    path('finance/recurring/create', RecurringTransactionCreateView.as_view(), name='recurring-finance-create'),
    path('finance/recurring/<int:rt_id>/edit', RecurringTransactionEditView.as_view(), name='recurring-finance-edit'),
    path('finance/recurring/<int:rt_id>/delete', RecurringTransactionDeleteView.as_view(), name='recurring-finance-delete'),
	path('water/add', WaterAddView.as_view(), name='water-add'),
    path('finance/recurring/generate', GenerateRecurringFinanceView.as_view(), name='recurring-finance-generate'),
	path('reports', ReportsView.as_view(), name='reports'),
    path('tasks/recurring/generate', GenerateRecurringTasksView.as_view(), name='recurring-tasks-generate'),
] 