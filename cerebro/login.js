// SkillTwin HQ - Login Logic

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("login-form");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const submitBtn = document.getElementById("submit-btn");
  const clearBtn = document.getElementById("clear-btn");
  const forgotLink = document.getElementById("forgot-link");

  const emailError = document.getElementById("email-error");
  const passwordError = document.getElementById("password-error");

  // Estado para evitar múltiples envíos
  let isSubmitting = false;

  // Utilidades de validación
  const validators = {
    email: (value) => {
      if (!value) return "El correo es obligatorio";
      const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!regex.test(value)) return "Formato de correo inválido";
      return null;
    },
    password: (value) => {
      if (!value) return "La contraseña es obligatoria";
      if (value.length < 8) return "La contraseña debe tener al menos 8 caracteres";
      return null;
    }
  };

  // Mostrar error en campo
  function showError(inputEl, errorEl, message) {
    inputEl.classList.add("error");
    errorEl.textContent = message;
    errorEl.classList.add("visible");
  }

  // Limpiar error de campo
  function clearError(inputEl, errorEl) {
    inputEl.classList.remove("error");
    errorEl.textContent = "";
    errorEl.classList.remove("visible");
  }

  // Validar un campo individual
  function validateField(inputEl, errorEl, validator) {
    const error = validator(inputEl.value.trim());
    if (error) {
      showError(inputEl, errorEl, error);
      return false;
    }
    clearError(inputEl, errorEl);
    return true;
  }

  // Validar todo el formulario
  function validateForm() {
    const emailValid = validateField(emailInput, emailError, validators.email);
    const passwordValid = validateField(passwordInput, passwordError, validators.password);
    return emailValid && passwordValid;
  }

  // Estado de carga del botón
  function setLoading(loading) {
    isSubmitting = loading;
    submitBtn.classList.toggle("loading", loading);
    submitBtn.disabled = loading;
    clearBtn.disabled = loading;
    emailInput.disabled = loading;
    passwordInput.disabled = loading;
  }

  // Limpiar formulario
  function clearForm() {
    form.reset();
    clearError(emailInput, emailError);
    clearError(passwordInput, passwordError);
    emailInput.focus();
  }

  // Manejar envío
  async function handleSubmit(e) {
    e.preventDefault();
    if (isSubmitting) return;

    if (!validateForm()) {
      // Enfocar primer campo con error
      const firstError = form.querySelector(".form-input.error");
      if (firstError) firstError.focus();
      return;
    }

    setLoading(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: emailInput.value.trim(),
          password: passwordInput.value // No trim para preservar espacios intencionales
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Credenciales inválidas");
      }

      // Éxito: Guardar token y redirigir
      localStorage.setItem("skilltwin_token", data.token);
      localStorage.setItem("skilltwin_user", JSON.stringify(data.user));
      
      // Redirigir a home (que luego redirige al dashboard)
      window.location.href = "home.html";

    } catch (error) {
      // Error: Mostrar mensaje bajo el formulario (usamos el error de password como contenedor general)
      showError(passwordInput, passwordError, error.message);
      passwordInput.focus();
    } finally {
      setLoading(false);
    }
  }

  // Validación en tiempo real al escribir
  emailInput.addEventListener("input", () => {
    if (emailInput.classList.contains("error")) {
      validateField(emailInput, emailError, validators.email);
    }
  });

  passwordInput.addEventListener("input", () => {
    if (passwordInput.classList.contains("error")) {
      validateField(passwordInput, passwordError, validators.password);
    }
  });

  // Enter key en cualquier campo envía el formulario
  form.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !isSubmitting) {
      e.preventDefault();
      handleSubmit(e);
    }
  });

  form.addEventListener("submit", handleSubmit);
  clearBtn.addEventListener("click", clearForm);

  // Auto-focus en email al cargar
  emailInput.focus();
});