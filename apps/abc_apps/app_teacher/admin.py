from django.contrib import admin

from apps.abc_apps.app_teacher.models import ClassGeneralRemark, Homework, HomeworkSubmission, StudentMonthlyObjective, StudentProofScan, StudentRemark, WeeklyTeachingPlan

# Register your models here.

admin.site.register(WeeklyTeachingPlan)
admin.site.register(StudentMonthlyObjective)
admin.site.register(ClassGeneralRemark)
admin.site.register(StudentProofScan)
admin.site.register(StudentRemark)
admin.site.register(Homework)
admin.site.register(HomeworkSubmission)
