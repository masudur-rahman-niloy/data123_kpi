from django.core.exceptions import ValidationError
from djstripe.models import (
    Price,
    Product,
    Subscription,
    SubscriptionItem,
)
from rest_framework import serializers

from kobo.apps.stripe.models import PlanAddOn


class OneTimeAddOnSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanAddOn
        fields = (
            'id',
            'created',
            'is_available',
            'usage_limits',
            'limits_used',
            'organization',
            'product',
        )


class BaseProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'type', 'metadata')


class BasePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = (
            'id',
            'nickname',
            'currency',
            'type',
            'recurring',
            'unit_amount',
            'human_readable_price',
            'metadata',
        )


class PriceIdSerializer(serializers.Serializer):
    price_id = serializers.SlugRelatedField(
        'id',
        queryset=Price.objects.filter(active=True, product__active=True),
        required=True,
        allow_empty=False,
    )

    class Meta:
        model = Price
        fields = ('id',)


class ChangePlanSerializer(PriceIdSerializer):
    subscription_id = serializers.SlugRelatedField(
        'id',
        queryset=Subscription.objects.filter(
            status__in=['active'],
        ),
        required=True,
        allow_empty=False,
    )

    class Meta:
        model = Subscription
        fields = ('id',)


class CustomerPortalSerializer(serializers.Serializer):
    organization_id = serializers.CharField(required=True)

    def validate_organization_id(self, organization_id):
        if organization_id.startswith('org'):
            return organization_id
        raise ValidationError('Invalid organization ID')


class CheckoutLinkSerializer(PriceIdSerializer, CustomerPortalSerializer):
    organization_id = serializers.CharField(required=False)


class PriceSerializer(BasePriceSerializer):
    product = BaseProductSerializer()

    class Meta(BasePriceSerializer.Meta):
        fields = (
            'id',
            'nickname',
            'currency',
            'type',
            'recurring',
            'unit_amount',
            'human_readable_price',
            'metadata',
            'product',
        )


class ProductSerializer(BaseProductSerializer):
    prices = BasePriceSerializer(many=True)

    class Meta(BaseProductSerializer.Meta):
        fields = ('id', 'name', 'description', 'type', 'prices', 'metadata')


class SubscriptionItemSerializer(serializers.ModelSerializer):
    price = PriceSerializer()

    class Meta:
        model = SubscriptionItem
        fields = ('id', 'price')


class SubscriptionSerializer(serializers.ModelSerializer):
    items = SubscriptionItemSerializer(many=True)

    class Meta:
        model = Subscription
        exclude = ('djstripe_id',)
