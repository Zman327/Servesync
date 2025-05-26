function openLoginModal() {
  document.getElementById("loginModal").style.display = "flex";
}

function closeLoginModal() {
  document.getElementById("loginModal").style.display = "none";
}

window.onclick = function(event) {
  const modal = document.getElementById("loginModal");
  if (event.target === modal) {
    closeLoginModal();
  }
};

// Close modal on Escape key
window.addEventListener("keydown", function(e) {
  if (e.key === "Escape") {
    closeLoginModal();
  }
});

// Toggle password visibility
function togglePasswordVisibility() {
  const pwField = document.getElementById("password");
  const toggle = document.getElementById("togglePassword");
  const lockIcon = document.getElementById("lockIcon");

  if (pwField.type === "password") {
    pwField.type = "text";
    toggle.classList.remove("bxs-eye");
    toggle.classList.add("bxs-hide");

    lockIcon.classList.remove("bxs-lock-alt");
    lockIcon.classList.add("bxs-lock-open-alt");
  } else {
    pwField.type = "password";
    toggle.classList.remove("bxs-hide");
    toggle.classList.add("bxs-eye");

    lockIcon.classList.remove("bxs-lock-open-alt");
    lockIcon.classList.add("bxs-lock-alt");
  }
}

let dropdownTimeout;

const dropdown = document.querySelector(".dropdown");

if (dropdown) {
  dropdown.addEventListener("mouseenter", () => {
    clearTimeout(dropdownTimeout);
    const content = dropdown.querySelector(".dropdown-content");
    if (content) content.style.display = "block";
  });

  dropdown.addEventListener("mouseleave", () => {
    dropdownTimeout = setTimeout(() => {
      const content = dropdown.querySelector(".dropdown-content");
      if (content) content.style.display = "none";
    }, 100); // Delay in milliseconds
  });
}

window.onload = function () {
  const flashMessages = document.querySelector(".flash-messages");
  if (flashMessages) {
    openLoginModal();
    setTimeout(() => {
      document.querySelectorAll('input.error').forEach(input => {
        input.classList.remove('error');
      });
    }, 1000);
  }
};

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.querySelector("#loginModal form");
  const loginErrorMessage = document.getElementById("login-error-message");

  if (loginForm) {
    loginForm.addEventListener("submit", function (e) {
      const usernameInput = loginForm.querySelector("#username");
      const passwordInput = loginForm.querySelector("#password");
      const username = usernameInput.value.trim();
      const password = passwordInput.value.trim();

      let hasError = false;

      if (!username) {
        usernameInput.classList.add("input-error");
        const usernameLabel = loginForm.querySelector("label[for='username']");
        const usernameIcon = loginForm.querySelector("#username-icon");
        if (usernameLabel) usernameLabel.classList.add("label-error");
        if (usernameIcon) usernameIcon.classList.add("input-error-icon");
        hasError = true;
      }

      if (!password) {
        passwordInput.classList.add("input-error");
        const passwordLabel = loginForm.querySelector("label[for='password']");
        const passwordIcon = loginForm.querySelector("#lockIcon");
        if (passwordLabel) passwordLabel.classList.add("label-error");
        if (passwordIcon) passwordIcon.classList.add("input-error-icon");
        hasError = true;
      }

      if (hasError) {
        loginErrorMessage.style.display = "block";
        loginErrorMessage.classList.remove("fade-out");

        setTimeout(() => {
          loginErrorMessage.classList.add("fade-out");

          setTimeout(() => {
            loginErrorMessage.style.display = "none";
            loginErrorMessage.classList.remove("fade-out");
          }, 500);
        }, 2000);

        setTimeout(() => {
          usernameInput.classList.remove("input-error");
          passwordInput.classList.remove("input-error");

          const usernameLabel = loginForm.querySelector("label[for='username']");
          const passwordLabel = loginForm.querySelector("label[for='password']");
          const usernameIcon = loginForm.querySelector("#username-icon");
          const passwordIcon = loginForm.querySelector("#lockIcon");

          if (usernameLabel) usernameLabel.classList.remove("label-error");
          if (passwordLabel) passwordLabel.classList.remove("label-error");
          if (usernameIcon) usernameIcon.classList.remove("input-error-icon");
          if (passwordIcon) passwordIcon.classList.remove("input-error-icon");
        }, 800);

        e.preventDefault();
      }
    });
  }
});
