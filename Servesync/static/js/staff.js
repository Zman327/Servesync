let modalEdited = false;
function openReviewModal(log) {
  modalEdited = false;
  document.getElementById('modal-student').innerText = `${log.student_name} (${log.user_id})`;
  document.getElementById('modal-activity').innerText = log.description;
  document.getElementById('modal-hours').innerText = log.hours;
  document.getElementById('modal-date').innerText = log.formatted_date;
  document.getElementById('modal-status').innerText = log.status_label;
  document.getElementById('modal-student-img').src = log.picture_url;
  document.getElementById('modal-group').innerText = log.group || "N/A";
  document.getElementById('modal-log-time').innerText = log.formatted_log_time;
  document.getElementById('approve-log-id').value = log.id;
  document.getElementById('reject-log-id').value = log.id;
  document.getElementById('edit-log-id').value = log.id;

  document.getElementById('reviewModal').style.display = 'block';
}

function closeModal() {
  document.getElementById('reviewModal').style.display = 'none';
  if (modalEdited) {
    window.location.reload();
  }
}

function openReportModal() {
  document.getElementById('reportModal').style.display = 'block';
}

function closeReportModal() {
  document.getElementById('reportModal').style.display = 'none';
}

function openApproveTipsModal() {
  document.getElementById('approveTipsModal').style.display = 'block';
}

function closeApproveTipsModal() {
  document.getElementById('approveTipsModal').style.display = 'none';
}

window.onclick = function(event) {
  const reviewModal = document.getElementById('reviewModal');
  const reportModal = document.getElementById('reportModal');
  const approveTipsModal = document.getElementById('approveTipsModal');
  const manageGroupModal = document.getElementById('manageGroupModal');
  if (event.target === reviewModal) {
    reviewModal.style.display = "none";
  } else if (event.target === reportModal) {
    reportModal.style.display = "none";
  } else if (event.target === approveTipsModal) {
    approveTipsModal.style.display = "none";
  } else if (event.target === manageGroupModal) {
    manageGroupModal.style.display = "none";
  }
}

function makeEditable(id) {
  const el = document.getElementById(id);
  el.contentEditable = true;
  el.focus();
  el.classList.add("editing");

  function handleKey(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      el.blur();
    }
  }

  function handleBlur() {
    el.contentEditable = false;
    el.classList.remove("editing");
    el.removeEventListener("blur", handleBlur);
    el.removeEventListener("keydown", handleKey);
    saveEdits();
  }

  el.addEventListener("keydown", handleKey);
  el.addEventListener("blur", handleBlur);
}

function saveEdits() {
  const logId = document.getElementById('edit-log-id').value;

  const rawDate = document.getElementById('modal-date').innerText.trim();
  const parsedDate = new Date(rawDate);
  const formattedDate = ("0" + parsedDate.getDate()).slice(-2) + "-" +
                        ("0" + (parsedDate.getMonth() + 1)).slice(-2) + "-" +
                        parsedDate.getFullYear();

  const data = {
    log_id: logId,
    description: document.getElementById('modal-activity').innerText.trim(),
    hours: document.getElementById('modal-hours').innerText.trim(),
    date: formattedDate
  };

  fetch('/update-log-field', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
  .then(response => response.json())
  .then(result => {
    modalEdited = true;
  });
}

function openManageGroupModal() {
  document.getElementById('manageGroupModal').style.display = 'block';
}

function closeManageGroupModal() {
  document.getElementById('manageGroupModal').style.display = 'none';
}

document.addEventListener('DOMContentLoaded', function () {
  // --- Existing group form logic ---
  const form = document.getElementById('manageGroupForm');
  if (form) {
    form.addEventListener('submit', function(event) {
      event.preventDefault();
      var groupId = document.getElementById('groupSelect').value;
      var groupName = document.getElementById('groupName').value;

      fetch('/update-group', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          groupId: groupId,
          groupName: groupName
        })
      }).then(response => response.json())
        .then(data => {
          if (data.success) {
            alert('Group updated successfully');
          } else {
            alert('Error updating group');
          }
          closeManageGroupModal();
        });
    });
  }

  // --- Appended logic from /submissions.html ---
  const rows = Array.from(document.querySelectorAll("#submissionsTable tbody tr"));
  const rowsPerPage = 10;
  let currentPage = 1;
  const totalPages = Math.ceil(rows.length / rowsPerPage);
  const pageIndicator = document.getElementById("pageIndicator");
  const prevBtn = document.getElementById("prevPage");
  const nextBtn = document.getElementById("nextPage");

  function showPage(page) {
    const start = (page - 1) * rowsPerPage;
    const end = start + rowsPerPage;
    rows.forEach((row, index) => {
      row.style.display = index >= start && index < end ? "" : "none";
    });
    if (pageIndicator) pageIndicator.textContent = `Page ${page}`;
    if (prevBtn) prevBtn.disabled = page === 1;
    if (nextBtn) nextBtn.disabled = page === totalPages || totalPages === 0;
  }

  if (prevBtn && nextBtn) {
    prevBtn.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage--;
        showPage(currentPage);
      }
    });

    nextBtn.addEventListener("click", () => {
      if (currentPage < totalPages) {
        currentPage++;
        showPage(currentPage);
      }
    });
  }

  // Default sort by Date (column 3) descending
  rows.sort((a, b) => {
    const cellA = a.cells[3].innerText;
    const cellB = b.cells[3].innerText;
    return new Date(cellB) - new Date(cellA);
  });
  rows.forEach(row => row.parentNode.appendChild(row));
  showPage(currentPage);

  // Sorting functionality
  let currentSortedColumn = null;
  let currentSortAsc = true;

  document.querySelectorAll(".sortable").forEach(header => {
    header.addEventListener("click", () => {
      const column = parseInt(header.getAttribute("data-column"));

      document.querySelectorAll(".sortable").forEach(h => h.classList.remove("asc", "desc"));
      document.querySelectorAll(".sort-icon").forEach(icon => icon.classList.remove("active"));

      if (currentSortedColumn === column) {
        currentSortAsc = !currentSortAsc;
      } else {
        currentSortAsc = true;
        currentSortedColumn = column;
      }

      header.classList.add(currentSortAsc ? "asc" : "desc");

      const icon = header.querySelector(".sort-icon");
      if (icon) icon.classList.add("active");

      rows.sort((a, b) => {
        const cellA = a.cells[column].innerText;
        const cellB = b.cells[column].innerText;

        if (column === 3) {
          return currentSortAsc
            ? new Date(cellA) - new Date(cellB)
            : new Date(cellB) - new Date(cellA);
        }

        const valA = cellA.toLowerCase();
        const valB = cellB.toLowerCase();

        if (!isNaN(valA) && !isNaN(valB)) {
          return currentSortAsc ? valA - valB : valB - valA;
        }

        return currentSortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
      });

      rows.forEach(row => row.parentNode.appendChild(row));
      showPage(currentPage);
    });
  });

  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", function () {
      const searchTerm = searchInput.value.toLowerCase();

      rows.forEach(row => {
        const studentName = row.cells[0].textContent.toLowerCase();
        const date = row.cells[3].textContent.toLowerCase();
        const group = row.cells[5].textContent.toLowerCase();

        if (studentName.includes(searchTerm) || date.includes(searchTerm) || group.includes(searchTerm)) {
          row.style.display = "";
        } else {
          row.style.display = "none";
        }
      });
    });
  }

  document.querySelectorAll('.submission-row').forEach(function(row) {
    row.addEventListener('click', function() {
      const studentName = this.getAttribute('data-student-name');
      const pictureUrl = this.getAttribute('data-picture-url');
      const userId = this.getAttribute('data-user-id');
      const description = this.getAttribute('data-description');
      const hours = this.getAttribute('data-hours');
      const date = this.getAttribute('data-date');
      const formattedDate = this.getAttribute('data-formatted-date');
      const statusLabel = this.getAttribute('data-status-label');
      const group = this.getAttribute('data-group');
      const formattedLogTime = this.getAttribute('data-formatted-log-time');
      const id = this.getAttribute('data-id');

      document.getElementById('modal-student').innerText = `${studentName} (${userId})`;
      document.getElementById('modal-activity').innerText = description;
      document.getElementById('modal-hours').innerText = hours;
      document.getElementById('modal-date').innerText = formattedDate || date;
      document.getElementById('modal-status').innerText = statusLabel;
      document.getElementById('modal-group').innerText = group || "N/A";
      document.getElementById('modal-log-time').innerText = formattedLogTime || "N/A";
      document.getElementById('approve-log-id').value = id;
      document.getElementById('reject-log-id').value = id;
      document.getElementById('edit-log-id').value = id;
      document.getElementById('modal-student-img').src = pictureUrl || '/static/default-profile.png';

      document.getElementById('reviewModal').style.display = 'block';
    });
  });
});