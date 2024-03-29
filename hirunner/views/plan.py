#!/usr/bin/python
# encoding=utf-8

from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from hirunner.models import Plan, PlanCase, Case, PlanResult
from hirunner.serializers import PlanSerializer, PlanCaseSerializer, PlanResultSerializer
from hirunner.views.run import run_plan_engine
from hirunner.views.task import scheduler
from user.pagination import CustomPagination


class PlanViewSet(ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer

    def create(self, request, *args, **kwargs):
        name = request.data.get("name")
        try:
            plan = Plan.objects.get(name=name)
            return Response(f"plan {plan.name} existed", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ObjectDoesNotExist:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)

            plan = Plan.objects.get(name=request.data.get("name"))
            project_id = request.data.get("projectId")
            task_run_env = request.data.get("taskRunEnv")
            task_status = request.data.get("taskStatus")
            task_crontab = request.data.get("taskCrontab")
            task_added = ""
            if task_status == "1":
                run_user_nickname = "定时任务"
                user_id = "task"
                task_added = scheduler.add_job(func=run_plan_engine,
                                               trigger=CronTrigger.from_crontab(task_crontab),
                                               id=str(plan.id),
                                               args=[project_id, plan.id, task_run_env, run_user_nickname, user_id],
                                               max_instances=1,
                                               replace_existing=True)
            data = serializer.data
            data["taskAdded"] = str(task_added)
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        name = request.data.get("name")
        plan_id = kwargs["pk"]
        try:
            plan = Plan.objects.get(name=name)
            if plan_id != plan.id:
                return Response(f"plan {plan.name} existed ", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ObjectDoesNotExist:
            pass

        project_id = request.data.get("projectId")
        task_run_env = request.data.get("taskRunEnv")
        task_status = request.data.get("taskStatus")
        task_crontab = request.data.get("taskCrontab")
        task_updated = ""

        if task_status == "1":
            run_user_nickname = "定时任务"
            user_id = "task"
            task_updated = scheduler.add_job(func=run_plan_engine,
                                             trigger=CronTrigger.from_crontab(task_crontab),
                                             id=str(plan_id),
                                             args=[project_id, plan_id, task_run_env, run_user_nickname, user_id],
                                             max_instances=1,
                                             replace_existing=True)
        if task_status == "0":
            try:
                task_updated = scheduler.remove_job(str(plan_id))
            except JobLookupError:
                task_updated = "task removed"

        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        data = serializer.data
        data["taskUpdated"] = str(task_updated)
        return Response(data)

    def list(self, request, *args, **kwargs):
        project_id = request.GET.get("projectId")
        query = Q(project_id=project_id)
        plan_name = request.GET.get("name")
        if plan_name:
            query &= Q(name__icontains=plan_name)
        queryset = Plan.objects.filter(query).order_by('-id')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        plan_id = kwargs["pk"]
        plan_case = PlanCase.objects.filter(plan_id=plan_id)
        if plan_case:
            return Response({"msg": "请先删除关联测试用例"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            try:
                scheduler.remove_job(str(plan_id))
            except JobLookupError:
                pass
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)


class PlanCaseView(ModelViewSet):
    queryset = PlanCase.objects.all()
    serializer_class = PlanCaseSerializer

    def list(self, request, *args, **kwargs):
        plan_id = kwargs["plan_id"]
        query = Q(plan_id=plan_id)
        keyword = request.GET.get("keyword")
        if keyword:
            try:
                int(keyword)
                case_id_query = Q(case_id=keyword)
            except ValueError:
                case_id_query = Q()
            case_desc_query = Q(case_id__in=[case.id for case in Case.objects.filter(Q(desc__icontains=keyword))])
            query &= (case_id_query | case_desc_query)
        queryset = PlanCase.objects.filter(query).order_by("-case_id")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def add(self, request, *args, **kwargs):
        plan_id = kwargs["plan_id"]
        case_ids = request.data.get("caseIds")
        for case_id in case_ids:
            try:
                PlanCase.objects.get(plan_id=plan_id, case_id=case_id)
            except ObjectDoesNotExist:
                data = {
                    "planId": plan_id,
                    "caseId": case_id
                }
                serializer = PlanCaseSerializer(data=data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
        return Response({"caseIds": case_ids}, status=status.HTTP_201_CREATED)

    def remove(self, request, *args, **kwargs):
        plan_id = kwargs["plan_id"]
        case_id = kwargs["case_id"]
        plan_case = PlanCase.objects.get(plan_id=plan_id, case_id=case_id)
        plan_case.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def result(request, *args, **kwargs):
    search_type = request.GET.get("searchType")
    plan_id = kwargs["plan_id"]
    query = Q(plan_id=plan_id)
    if search_type == "passed":
        query &= Q(result__icontains="passed")
        query &= ~Q(result__icontains="failed")
        query &= ~Q(result__icontains="error")
    elif search_type == "failed":
        query &= Q(result__icontains="failed")
        query &= ~Q(result__icontains="error")
    elif search_type == "error":
        query &= Q(result__icontains="error")
    plan_result = PlanResult.objects.filter(query)
    cp = CustomPagination()
    page = cp.paginate_queryset(plan_result, request=request)
    if page is not None:
        serializer = PlanResultSerializer(page, many=True)
        return cp.get_paginated_response(serializer.data)


@api_view(['GET'])
def case_result(request, *args, **kwargs):
    plan_id = kwargs["plan_id"]
    case_id = kwargs["case_id"]
    case = Case.objects.get(id=case_id)
    plan_result = PlanResult.objects.filter(plan_id=plan_id, case_id=case_id).order_by('-run_time')
    plan_result = plan_result[0]
    data = {
        "planId": plan_id,
        "caseId": case_id,
        "caseDesc": case.desc,
        "caseCreatorNickname": case.creator_nickname,
        "result": plan_result.result,
        "elapsed": plan_result.elapsed,
        "output": plan_result.output,
        "runEnv": plan_result.run_env,
        "runUserNickname": plan_result.run_user_nickname,
        "runTime": plan_result.run_time.strftime("%Y-%m-%d %H:%M:%S")
    }
    return Response(data, status=status.HTTP_200_OK)
