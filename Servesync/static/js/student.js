document.addEventListener("DOMContentLoaded", () => {
  function showGroupError(show) {
    const errorBox = document.getElementById("group-error");
    const helperText = document.getElementById("group-helper-text");
    if (show) {
      const groupInput = document.getElementById("group");
      const container = groupInput.closest(".form-group");
      if (container && errorBox.parentNode !== container.parentNode) {
        container.parentNode.insertBefore(errorBox, container.nextSibling);
      }
      errorBox.style.display = "block";
      helperText.style.display = "none";
    } else {
      errorBox.style.display = "none";
      helperText.style.display = "block";
    }
  }

  const dateInput = document.getElementById("date");
  if (dateInput) {
    const today = new Date();
    const localDate = today.toLocaleDateString('en-CA'); // formats as YYYY-MM-DD
    dateInput.setAttribute("max", localDate);
    dateInput.value = localDate;
    const currentYear = today.getFullYear();
    const minDate = `${currentYear}-01-01`;
    dateInput.setAttribute("min", minDate);
  }

  // Confirmation message animation with auto-dismiss
  const confirmation = document.getElementById("confirmation-message");
  if (confirmation) {
    confirmation.classList.add("show");
    confirmation.scrollIntoView({ behavior: "smooth" });
    setTimeout(() => {
      confirmation.style.opacity = "0";
      setTimeout(() => confirmation.remove(), 500);
    }, 5000);
  }

  // Form validation and submit animation
  const form = document.querySelector("form");
  if (form) {
    form.addEventListener("submit", (e) => {
      document.getElementById("form-error-message").style.display = "none";
      let hasError = false;
      form.querySelectorAll("input[required]").forEach((input) => {
        if (!input.value.trim()) {
          input.classList.add("input-error");
          const icon = input.parentElement.querySelector('i');
          const label = input.parentElement.querySelector('label');
          if (icon) {
            icon.classList.add("input-error-icon");
            setTimeout(() => icon.classList.remove("input-error-icon"), 600);
          }
          if (label) {
            label.classList.add("label-error");
            setTimeout(() => label.classList.remove("label-error"), 600);
          }
          hasError = true;
          setTimeout(() => input.classList.remove("input-error"), 600);
        }
      });

      const hoursInput = document.getElementById("hours");
      const hours = parseFloat(hoursInput.value);
      if (hours <= 0) {
        hoursInput.classList.add("input-error");
        const hoursIcon = hoursInput.parentElement.querySelector('i');
        const hoursLabel = hoursInput.parentElement.querySelector('label');
        if (hoursIcon) {
          hoursIcon.classList.add("input-error-icon");
          setTimeout(() => hoursIcon.classList.remove("input-error-icon"), 600);
        }
        if (hoursLabel) {
          hoursLabel.classList.add("label-error");
          setTimeout(() => hoursLabel.classList.remove("label-error"), 600);
        }
        alert("Hours must be greater than 0.");
        e.preventDefault();
        return;
      }

      if (hasError) {
        const errorMessage = document.getElementById("form-error-message");
        errorMessage.style.display = "block";
        errorMessage.classList.remove("fade-out"); // reset if already fading

        setTimeout(() => {
          errorMessage.classList.add("fade-out");
          setTimeout(() => {
            errorMessage.style.display = "none";
            errorMessage.classList.remove("fade-out");
          }, 500); // match the CSS transition duration
        }, 2000); // visible for 2 seconds
        e.preventDefault();
        return;
      }

      const btnText = form.querySelector(".btn-text");
      const btnLoader = form.querySelector(".btn-loader");
      if (btnText && btnLoader) {
        btnText.style.display = "none";
        btnLoader.style.display = "inline-block";
      }
    });
  }

  const groupInput = document.getElementById("group");
  const suggestionBox = document.getElementById("group-suggestions");

  let timeout;
  groupInput.addEventListener("input", () => {
    clearTimeout(timeout);
    const query = groupInput.value.trim();
    if (!query) {
      suggestionBox.innerHTML = "";
      return;
    }
    timeout = setTimeout(() => {
      fetch(`/api/groups?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(groups => {
          suggestionBox.innerHTML = "";
          groups.forEach(group => {
            const li = document.createElement("li");
            li.textContent = group;
            li.addEventListener("click", () => {
              groupInput.value = group;
              showGroupError(false);

              // Clear error state if selecting from dropdown
              const errorBox = document.getElementById("group-error");
              const icon = groupInput.parentElement.querySelector("i");
              errorBox.style.display = "none";
              groupInput.classList.remove("input-error");
              if (icon) icon.classList.remove("input-error-icon");

              suggestionBox.innerHTML = "";

              // Fetch and populate the staff member linked to this group
              fetch(`/api/staff-for-group?group=${encodeURIComponent(group)}`)
                .then(res => res.json())
                .then(staff => {
                  const personSelect = document.getElementById("person_in_charge");
                  personSelect.value = "";
                  personSelect.setAttribute("data-linked-staff-value", "");
                  personSelect.setAttribute("data-linked-staff-label", "");

                  // Add the default auto-selected staff linked to the group
                  if (staff && staff.label) {
                    personSelect.value = staff.label;
                    personSelect.setAttribute("data-linked-staff-value", staff.value);
                    personSelect.setAttribute("data-linked-staff-label", staff.label);
                  }
                });
            });
            suggestionBox.appendChild(li);
          });
        });
    }, 200);
  });

  groupInput.addEventListener("blur", () => {
    const query = groupInput.value.trim();
    const errorBox = document.getElementById("group-error");
    const icon = groupInput.parentElement.querySelector("i");

    if (!query) {
      showGroupError(false);
      groupInput.classList.remove("input-error");
      if (icon) icon.classList.remove("input-error-icon");
      return;
    }

    fetch(`/api/groups?q=${encodeURIComponent(query)}`)
      .then(res => res.json())
      .then(groups => {
        const match = groups.some(group => group.toLowerCase() === query.toLowerCase());
        if (!match) {
          showGroupError(true);
          groupInput.classList.add("input-error");
          if (icon) icon.classList.add("input-error-icon");

          // Re-trigger animation
          groupInput.classList.remove("input-error");
          void groupInput.offsetWidth;
          groupInput.classList.add("input-error");

          if (icon) {
            icon.classList.remove("input-error-icon");
            void icon.offsetWidth;
            icon.classList.add("input-error-icon");
          }
        } else {
          showGroupError(false);
          groupInput.classList.remove("input-error");
          if (icon) icon.classList.remove("input-error-icon");
        }
      });
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".autocomplete-group")) {
      suggestionBox.innerHTML = "";
    }
  });

  const staffInput = document.getElementById("person_in_charge");
  const staffBox = document.getElementById("staff-suggestions");

  let staffTimeout;
  staffInput.addEventListener("input", () => {
    clearTimeout(staffTimeout);
    const query = staffInput.value.trim().toLowerCase();
    if (!query) {
      staffBox.innerHTML = "";
      return;
    }
    staffTimeout = setTimeout(() => {
      fetch(`/api/all-staff`)
        .then(res => res.json())
        .then(staffList => {
          staffBox.innerHTML = "";
          staffList.forEach(staff => {
            if (staff.label.toLowerCase().includes(query)) {
              const li = document.createElement("li");
              li.textContent = staff.label;
              li.addEventListener("click", () => {
                staffInput.value = staff.label;
                staffBox.innerHTML = "";
              });
              staffBox.appendChild(li);
            }
          });
        });
    }, 200);
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest("#person_in_charge")) {
      staffBox.innerHTML = "";
    }
  });
});