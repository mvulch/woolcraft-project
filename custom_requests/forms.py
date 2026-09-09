from django import forms

from .models import CustomRequest, CustomRequestMessage
from decimal import Decimal
from woolCraftProject.validators import validate_client_images, MultipleFileField

MAX_REQUEST_IMAGES = 3

class CustomRequestForm(forms.ModelForm):
    images = MultipleFileField(required=False, label='Примерни снимки (по избор)')

    class Meta:
        model = CustomRequest
        fields = ['title', 'description', 'specific_colors', 'size']
        labels = {
            'title': 'Заглавие',
            'description': 'Описание',
            'specific_colors': 'Конкретни желани цветове',
            'size': 'Ориентировъчен размер',
        }

    def clean_images(self):
        images = self.cleaned_data.get('images') or []
        if len(images) > MAX_REQUEST_IMAGES:
            raise forms.ValidationError(f'Можете да добавите най-много {MAX_REQUEST_IMAGES} снимки.')
        return [validate_client_images(image) for image in images]

class CustomRequestMessageForm(forms.ModelForm):
    class Meta:
        model = CustomRequestMessage
        fields = ['text']
        labels = {'text': 'Съобщение'}

class OfferPriceForm(forms.Form):
    offered_price = forms.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=Decimal('0.01'),
        max_value=Decimal('9999.99'),
        label='Предложена цена',
        error_messages={
            'invalid': 'Въведете валидна цена.',
            'min_value': 'Цената трябва да е положително число.',
            'max_value': 'Цената надвишава максималната допустима стойност.',
        }
    )