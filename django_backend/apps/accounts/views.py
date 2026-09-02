from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
    TokenVerifySerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from apps.accounts.models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": str(self.user.id),
            "email": self.user.email,
            "full_name": self.user.full_name,
        }
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer  # type: ignore[assignment]


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["message"] = "Token refreshed successfully"
        return data


class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer  # type: ignore[assignment]


class CustomTokenVerifySerializer(TokenVerifySerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["valid"] = True
        return data


class CustomTokenVerifyView(TokenVerifyView):
    serializer_class = CustomTokenVerifySerializer  # type: ignore[assignment]


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Enter your email", "autofocus": True}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Enter your password"}
        )
    )
    remember_me = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Enter password"}
        ),
        help_text="At least 8 characters",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirm password"}
        ),
        label="Confirm Password",
    )

    class Meta:
        model = User
        fields = ["email", "full_name"]
        widgets = {
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Enter your email"}
            ),
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter your full name"}
            ),
        }

    def clean_password_confirm(self):
        password = self.cleaned_data.get("password")
        password_confirm = self.cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match")
        return password_confirm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                if not form.cleaned_data["remember_me"]:
                    request.session.set_expiry(0)
                messages.success(request, f"Welcome back, {user.full_name or user.email}!")
                next_url = request.GET.get("next", "dashboard")
                return redirect(next_url)
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request, "Account created successfully! Welcome to RAG Postmortem Intelligence."
            )
            return redirect("dashboard")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login")


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


login_view = login_view
register_view = register_view
logout_view = logout_view
profile = ProfileView.as_view()
