import re
from django.contrib.auth import get_user_model
from django import forms
from django.contrib.auth.password_validation import validate_password

UserModel = get_user_model()

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(label="Парола", widget=forms.PasswordInput, validators=[validate_password])
    confirm_password = forms.CharField(label="Потвърдете парола", widget=forms.PasswordInput)

    class Meta:
        model = UserModel
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
        labels = {
            'username': 'Потребителско име',
            'email': 'Имейл адрес',
            'first_name': 'Име',
            'last_name': 'Фамилия',
        }
        help_texts = {
            'username': '',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if UserModel.objects.filter(email=email).exists():
            raise forms.ValidationError("Този имейл адрес вече е регистриран.")
        return email

    def clean_confirm_password(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Паролите не съвпадат.")

        return cleaned_data

    def save(self,commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.email_verified = False

        if commit:
            user.save()
        return user

class LoginForm(forms.Form):
    email = forms.EmailField(label="Имейл адрес", widget=forms.EmailInput)
    password = forms.CharField(label="Парола", widget=forms.PasswordInput)

class PhoneUpdateForm(forms.ModelForm):
    class Meta:
        model = UserModel
        fields = ['phone']
        labels = {'phone': 'Телефонен номер'}

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone and re.search(r'[^\W\d_]', phone, re.UNICODE):
            raise forms.ValidationError('Телефонният номер не може да съдържа букви.')
        return phone

