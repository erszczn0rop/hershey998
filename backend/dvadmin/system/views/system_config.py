# -*- coding: utf-8 -*-

"""
@author: 猿小天
@contact: QQ:1638245306
@Created on: 2022/1/21 003 0:30
@Remark: 系统配置
"""
import django_filters
from django.db.models import Q
from django_filters.rest_framework import BooleanFilter
from rest_framework import serializers

from dvadmin.system.models import SystemConfig
from dvadmin.utils.filters import DataLevelPermissionsFilter
from dvadmin.utils.json_response import DetailResponse, SuccessResponse, ErrorResponse
from dvadmin.utils.models import get_all_models_objects
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.validator import CustomValidationError
from dvadmin.utils.viewset import CustomModelViewSet


class SystemConfigCreateSerializer(CustomModelSerializer):
    """
    系统配置-新增时使用-序列化器
    """
    form_item_type_label = serializers.CharField(source='get_form_item_type_display', read_only=True)

    class Meta:
        model = SystemConfig
        fields = "__all__"
        read_only_fields = ["id"]


    def validate_key(self, value):
        """
        验证key是否允许重复
        parent为空时不允许重复,反之允许
        """
        instance = SystemConfig.objects.filter(key=value,parent__isnull=True).exists()
        if instance:
            raise CustomValidationError('已存在相同变量名')
        return value

class SystemConfigSerializer(CustomModelSerializer):
    """
    系统配置-序列化器
    """
    form_item_type_label = serializers.CharField(source='get_form_item_type_display', read_only=True)

    class Meta:
        model = SystemConfig
        fields = "__all__"
        read_only_fields = ["id"]


class SystemConfigChinldernSerializer(CustomModelSerializer):
    """
    系统配置子级-序列化器
    """
    chinldern = serializers.SerializerMethodField()
    form_item_type_label = serializers.CharField(source='get_form_item_type_display', read_only=True)

    def get_chinldern(self, instance):
        queryset = SystemConfig.objects.filter(parent=instance)
        if queryset:
            serializer = SystemConfigSerializer(queryset, many=True)
            return serializer.data
        return None

    class Meta:
        model = SystemConfig
        fields = "__all__"
        read_only_fields = ["id"]


class SystemConfigListSerializer(CustomModelSerializer):
    """
    系统配置下模块的保存-序列化器
    """

    def update(self, instance, validated_data):
        instance_mapping = {obj.id: obj for obj in instance}
        data_mapping = {item['id']: item for item in validated_data}
        for obj_id, data in data_mapping.items():
            instance_obj = instance_mapping.get(obj_id, None)
            if instance_obj is None:
                return SystemConfig.objects.create(**data)
            else:
                return instance_obj.objects.update(**data)

    class Meta:
        model = SystemConfig
        fields = "__all__"
        read_only_fields = ["id"]


class SystemConfigSaveSerializer(serializers.Serializer):
    class Meta:
        read_only_fields = ["id"]
        list_serializer_class = SystemConfigListSerializer


class SystemConfigFilter(django_filters.rest_framework.FilterSet):
    """
    过滤器
    """
    parent__isnull = BooleanFilter(field_name='parent', lookup_expr="isnull")

    class Meta:
        model = SystemConfig
        fields = ['id', 'parent', 'status', 'parent__isnull']





class SystemConfigViewSet(CustomModelViewSet):
    """
    系统配置接口
    list:查询
    create:新增
    update:修改
    retrieve:详情
    destroy:删除
    """
    queryset = SystemConfig.objects.order_by('sort', 'create_datetime')
    serializer_class = SystemConfigChinldernSerializer
    create_serializer_class = SystemConfigCreateSerializer
    retrieve_serializer_class = SystemConfigChinldernSerializer
    # filter_fields = ['id','parent']
    filter_class = SystemConfigFilter

    def save_content(self, request):
        body = request.data
        data_mapping = {item['id']: item for item in body}
        for obj_id, data in data_mapping.items():
            instance_obj = SystemConfig.objects.filter(id=obj_id).first()
            if instance_obj is None:
                # return SystemConfig.objects.create(**data)
                serializer = SystemConfigCreateSerializer(data=data)
            else:
                serializer = SystemConfigCreateSerializer(instance_obj, data=data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
        return DetailResponse(msg="保存成功")

    def get_association_table(self, request):
        """
        获取所有的model及字段信息
        """
        res = [ele.get('table') for ele in get_all_models_objects().values()]
        return DetailResponse(msg="获取成功", data=res)

    def get_table_data(self, request,pk):
        """
        动态获取关联表的数据
        """
        instance = SystemConfig.objects.filter(id=pk).first()
        if instance is None:
            return ErrorResponse(msg="查询出错了~")
        setting = instance.setting
        if setting is None:
            return ErrorResponse(msg="查询出错了~")
        table = setting.get('table') #获取model名
        model = get_all_models_objects(table).get("object", {})
        # 自己判断一下不存在
        queryset = model.objects.values()
        body = request.query_params
        search_value = body.get('search', None)
        if search_value:
            search_fields = setting.get('searchField')
            filters = Q()
            filters.connector = 'OR'
            for item in search_fields:
                filed = '{0}__icontains'.format(item.get('field'))
                filters.children.append((filed, search_value))
            queryset = model.objects.filter(filters).values()
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(queryset)
        return SuccessResponse(msg="获取成功", data=queryset, total=len(queryset))


    def get_relation_info(self,request):
        """
        查询关联的模板信息
        """
        body = request.query_params
        var_name = body.get('varName',None)
        table = body.get('table',None)
        instance = SystemConfig.objects.filter(key=var_name,setting__table=table).first()
        if instance is None:
            return ErrorResponse(msg="未获取到关联信息")
        relation_id = body.get('relationIds', None)
        relationIds = []
        if relation_id is None:
            return ErrorResponse(msg="未获取到关联信息")
        if instance.form_item_type in [13]:
            relationIds = [relation_id]
        elif instance.form_item_type in [14]:
            relationIds = relation_id.split(',')
        queryset = SystemConfig.objects.filter(value__in=relationIds).first()
        if queryset is None:
            return ErrorResponse(msg="未获取到关联信息")
        serializer = SystemConfigChinldernSerializer(queryset.parent)
        return DetailResponse(msg="查询成功",data=serializer.data)
