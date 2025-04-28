
  // Close modal with Escape key
  window.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeLoginModal();
    }
  });

  function togglePasswordVisibility() {
    const pwField = document.getElementById("password");
    const toggle = document.getElementById("togglePassword");
    if (pwField.type === "password") {
      pwField.type = "text";
      toggle.classList.remove("bxs-eye");
      toggle.classList.add("bxs-hide");
    } else {
      pwField.type = "password";
      toggle.classList.remove("bxs-hide");
      toggle.classList.add("bxs-eye");
    }
  }