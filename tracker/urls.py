from django.urls import path
from .views import DashboardView, QuickAddTaskView, ToggleTaskDoneView, QuickAddTransactionView, QuickAddSavingView, WaterAddView, ReportsView, SuggestTasksAIView, AddLearningLogView, AddHealthLogView, AddMindfulnessLogView, DeleteTransactionView

app_name = 'tracker'

urlpatterns = [
	path('', DashboardView.as_view(), name='dashboard'),
	path('tasks/add', QuickAddTaskView.as_view(), name='task-add'),
	path('tasks/<int:task_id>/toggle', ToggleTaskDoneView.as_view(), name='task-toggle'),
	path('tasks/suggest-ai', SuggestTasksAIView.as_view(), name='task-suggest-ai'),
	path('logs/learning/add', AddLearningLogView.as_view(), name='learning-add'),
	path('logs/health/add', AddHealthLogView.as_view(), name='health-add'),
	path('logs/mindfulness/add', AddMindfulnessLogView.as_view(), name='mindfulness-add'),
	path('finance/transaction/add', QuickAddTransactionView.as_view(), name='transaction-add'),
	path('finance/transaction/<int:transaction_id>/delete', DeleteTransactionView.as_view(), name='transaction-delete'),
	path('finance/saving/add', QuickAddSavingView.as_view(), name='saving-add'),
	path('water/add', WaterAddView.as_view(), name='water-add'),
	path('reports', ReportsView.as_view(), name='reports'),
] 