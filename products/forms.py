from django import forms
from .models import ProductReview, CourseQuestion, CourseQuestionReply
from woolCraftProject.validators import validate_client_images, MultipleFileField

MAX_REVIEW_IMAGES = 3

class ProductReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i,i) for i in range(1,6)],
        label='Оценка'
    )
    images = MultipleFileField(required=False, label='Снимки (по избор)')

    class Meta:
        model = ProductReview
        fields = ['rating','comment']
        labels = {'comment': 'Коментар'}
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Споделете мнението си за продукта...'}),
        }

    def clean_images(self):
        images = self.cleaned_data.get('images') or []
        if len(images) > MAX_REVIEW_IMAGES:
            raise forms.ValidationError(f'Можете да добавите най-много {MAX_REVIEW_IMAGES} снимки.')
        return [validate_client_images(image) for image in images]

class CourseQuestionForm(forms.ModelForm):
    class Meta:
        model = CourseQuestion
        fields = ['text', 'image']
        labels = {'text': 'Въпрос към урока', 'image': 'Снимка (по избор)'}

    def clean_image(self):
        return validate_client_images(self.cleaned_data.get('image'))


class CourseQuestionReplyForm(forms.ModelForm):
    class Meta:
        model = CourseQuestionReply
        fields = ['text', 'image']
        labels = {'text': 'Отговор', 'image': 'Снимка (по избор)'}

    def clean_image(self):
        return validate_client_images(self.cleaned_data.get('image'))
