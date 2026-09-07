from django import forms
from .models import ProductReview, CourseQuestion, CourseQuestionReply
from woolCraftProject.validators import validate_client_images

class ProductReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i,i) for i in range(1,6)],
        label='Оценка'
    )
    class Meta:
        model = ProductReview
        fields = ['rating','comment','image']
        labels = {'comment': 'Коментар', 'image': 'Снимка (по избор)'}

    def clean_image(self):
        return validate_client_images(self.cleaned_data.get('image'))

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
