from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

from dashboard.models import Profile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class ProfileForm(forms.ModelForm):
    """Data akun bawaan Django: nama dan email."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        taken = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError('This email is already used by another account.')
        return email


class ProfileDetailForm(forms.ModelForm):
    """Data tambahan di model Profile: phone dan address."""

    phone = forms.CharField(
        label='Phone number',
        required=False,
        max_length=20,
        validators=[RegexValidator(r'^\+?[0-9 ()-]{7,20}$', 'Use digits, spaces and an optional leading +.')],
        widget=forms.TextInput(attrs={'autocomplete': 'tel', 'placeholder': '+62 000 0000 0000'}),
    )

    class Meta:
        model = Profile
        fields = ['phone', 'address']
        widgets = {
            'address': forms.TextInput(attrs={'autocomplete': 'street-address', 'placeholder': 'Street, City, Country'}),
        }


class DeleteAccountForm(forms.Form):
    """Konfirmasi hapus akun: user harus mengetik ulang password."""

    password = forms.CharField(
        label='Confirm your password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.user.check_password(password):
            raise forms.ValidationError('That password is not correct.')
        return password