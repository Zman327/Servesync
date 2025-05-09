// General-purpose table sorting function
function sortTableByColumn(tableId, columnIndex, ascending = true) {
  const table = document.getElementById(tableId);
  const tbody = table.tBodies[0];
  const rows = Array.from(tbody.querySelectorAll("tr"));

  const sortedRows = rows.sort((a, b) => {
    const aText = a.children[columnIndex].textContent.trim().toLowerCase();
    const bText = b.children[columnIndex].textContent.trim().toLowerCase();

    const aVal = parseFloat(aText);
    const bVal = parseFloat(bText);

    if (!isNaN(aVal) && !isNaN(bVal)) {
      return ascending ? aVal - bVal : bVal - aVal;
    }
    return ascending ? aText.localeCompare(bText) : bText.localeCompare(aText);
  });

  sortedRows.forEach(row => tbody.appendChild(row));
}

document.querySelectorAll('.sidebar ul li a').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const target = link.getAttribute('data-target');
    document.querySelectorAll('.content-section').forEach(sec => sec.style.display = 'none');
    document.getElementById(`content-${target}`).style.display = 'block';
    document.querySelector('.sidebar ul li a.active')?.classList.remove('active');
    link.classList.add('active');
  });
});

// Register ChartDataLabels plugin
Chart.register(ChartDataLabels);

// Student Growth Over Time
new Chart(document.getElementById('chart-students-over-time'), {
  type: 'line',
  data: {
    labels: chartLabels,
    datasets: [{ 
      label: 'New Submissions',
      data: chartData,
      fill: false,
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1
    }]
  },
  options: { responsive: true, maintainAspectRatio: false }
});

// Sample Hours by Group (Bar)
new Chart(document.getElementById('chart-hours-by-group'), {
  type: 'bar',
  data: {
    labels: ['Group A','Group B','Group C','Group D'],
    datasets: [{
      label: 'Approved Hours',
      data: [120, 90, 150, 80]
    }]
  },
  options: { responsive: true, maintainAspectRatio: false }
});

// Award Distribution Chart (Pie)
new Chart(document.getElementById('chart-award-distribution'), {
  type: 'pie',
  data: {
    labels: awardLabels,
    datasets: [{
      data: awardCounts,
      backgroundColor: awardColors
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      datalabels: {
        color: '#fff',
        font: {
          weight: 'bold',
          size: 14
        },
        formatter: (value, context) => {
          const data = context.chart.data.datasets[0].data;
          const total = data.reduce((acc, val) => acc + val, 0);
          const percentage = (value / total) * 100;
          return percentage >= 1 ? `${percentage.toFixed(1)}%` : '';
        }
      }
    }
  },
  plugins: [ChartDataLabels]
});

document.addEventListener("DOMContentLoaded", function () {
  const rows = Array.from(document.querySelectorAll("#submissionsTable tbody tr"));
  const rowsPerPage = 7;
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
    pageIndicator.textContent = `Page ${page}`;
    prevBtn.disabled = page === 1;
    nextBtn.disabled = page === totalPages || totalPages === 0;
  }

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

  rows.sort((a, b) => {
    const cellA = a.cells[3].innerText;
    const cellB = b.cells[3].innerText;
    return new Date(cellB) - new Date(cellA);
  });
  rows.forEach(row => row.parentNode.appendChild(row));
  showPage(currentPage);

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
});

document.addEventListener("DOMContentLoaded", function () {
  const allRows = Array.from(document.querySelectorAll("#submissionsTable tbody tr"));
  const rowsPerPage = 7;
  let currentPage = 1;
  let filteredRows = [...allRows];

  const pageIndicator = document.getElementById("pageIndicator");
  const prevBtn = document.getElementById("prevPage");
  const nextBtn = document.getElementById("nextPage");
  const searchInput = document.getElementById("searchInput");

  function showPage(page) {
    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
    const start = (page - 1) * rowsPerPage;
    const end = start + rowsPerPage;

    allRows.forEach(row => row.style.display = "none");
    filteredRows.slice(start, end).forEach(row => row.style.display = "");

    pageIndicator.textContent = `Page ${page}`;
    prevBtn.disabled = page === 1;
    nextBtn.disabled = page === totalPages || totalPages === 0;
  }

  function updateSearchAndPagination() {
    const searchTerm = searchInput.value.toLowerCase();

    filteredRows = allRows.filter(row => {
      const studentName = row.cells[0].textContent.toLowerCase();
      const date = row.cells[3].textContent.toLowerCase();
      const group = row.cells[5].textContent.toLowerCase();
      return studentName.includes(searchTerm) || date.includes(searchTerm) || group.includes(searchTerm);
    });

    currentPage = 1;
    showPage(currentPage);
  }

  searchInput.addEventListener("input", updateSearchAndPagination);

  prevBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      showPage(currentPage);
    }
  });

  nextBtn.addEventListener("click", () => {
    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
    if (currentPage < totalPages) {
      currentPage++;
      showPage(currentPage);
    }
  });

  updateSearchAndPagination();
});

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

function closeModal() {
  document.getElementById('reviewModal').style.display = 'none';
  if (modalEdited) {
    window.location.reload();
  }
}

// Open Add Student Modal
function openAddStudentModal() {
  document.getElementById('addStudentModal').style.display = 'block';
}
// Close Add Student Modal
function closeAddStudentModal() {
  document.getElementById('addStudentModal').style.display = 'none';
}

function openBulkUploadModal() {
  document.getElementById('bulkUploadModal').style.display = 'block';
}

function closeBulkUploadModal() {
  document.getElementById('bulkUploadModal').style.display = 'none';
}

window.onclick = function(event) {
  const modal = document.getElementById('reviewModal');
  const addModal = document.getElementById('addStudentModal');
  const bulkModal = document.getElementById('bulkUploadModal');
  if (event.target === modal) {
    modal.style.display = "none";
  }
  if (event.target === addModal) closeAddStudentModal();
  if (event.target === bulkModal) closeBulkUploadModal();
}

let modalEdited = false;

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

// SEARCH AND PAGINATION FOR ALL STUDENTS TABLE
document.addEventListener("DOMContentLoaded", function () {
  const rows = Array.from(document.querySelectorAll("#studentsTable tbody tr"));
  const rowsPerPage = 7;
  let currentPage = 1;
  let filteredRows = [...rows];

  const pageIndicator = document.getElementById("studentPageIndicator");
  const prevBtn = document.getElementById("studentPrevPage");
  const nextBtn = document.getElementById("studentNextPage");
  const searchInput = document.getElementById("studentSearchInput");

  // Function to display rows for the current page
  function showPage(page) {
    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
    const start = (page - 1) * rowsPerPage;
    const end = start + rowsPerPage;

    // Hide all rows, then show only those in the current page range
    rows.forEach(row => row.style.display = "none");
    filteredRows.slice(start, end).forEach(row => row.style.display = "");

    pageIndicator.textContent = `Page ${page}`;
    prevBtn.disabled = page === 1;
    nextBtn.disabled = page === totalPages || totalPages === 0;
  }

  // Function to filter rows based on the search term and reset pagination
  function updateSearchAndPagination() {
    const searchTerm = searchInput.value.toLowerCase();

    filteredRows = rows.filter(row => {
      const schoolId = row.cells[0].textContent.toLowerCase();
      const name = row.cells[1].textContent.toLowerCase();
      const form = row.cells[2].textContent.toLowerCase();
      const award = row.cells[4].textContent.toLowerCase();
      return (
        schoolId.includes(searchTerm) ||
        name.includes(searchTerm) ||
        form.includes(searchTerm) ||
        award.includes(searchTerm)
      );
    });

    currentPage = 1;
    showPage(currentPage);
  }

  // Event listeners for search input and pagination buttons
  searchInput.addEventListener("input", updateSearchAndPagination);
  prevBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      showPage(currentPage);
    }
  });
  nextBtn.addEventListener("click", () => {
    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
    if (currentPage < totalPages) {
      currentPage++;
      showPage(currentPage);
    }
  });

  // Initialize display
  updateSearchAndPagination();
});
// Update "Choose File" label when file is selected
document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById("studentImage");
  const fileChosen = document.getElementById("file-chosen");

  if (fileInput && fileChosen) {
    fileInput.addEventListener("change", function () {
      fileChosen.textContent = this.files.length > 0 ? this.files[0].name : "No file chosen";
    });
  }
});
// Open Download Reports Modal
function openReportModal() {
  document.getElementById('reportModal').style.display = 'block';
}

// Close Download Reports Modal
function closeReportModal() {
  document.getElementById('reportModal').style.display = 'none';
}

document.addEventListener("DOMContentLoaded", function () {
  const openDownloadBtn = document.getElementById("openDownloadModal");
  if (openDownloadBtn) {
    openDownloadBtn.addEventListener("click", openReportModal);
  }
});

// Optionally close modal when clicking outside
window.addEventListener("click", function (event) {
  const reportModal = document.getElementById("reportModal");
  if (event.target === reportModal) {
    reportModal.style.display = "none";
  }
});
  // General-purpose sortable columns for any table with .sortable headers
  document.querySelectorAll(".sortable").forEach(header => {
    header.addEventListener("click", () => {
      const table = header.closest("table");
      const tableId = table.id;
      const columnIndex = parseInt(header.dataset.column);
      const currentAscending = header.classList.contains("asc");

      document.querySelectorAll(".sortable").forEach(h => h.classList.remove("asc", "desc"));
      header.classList.add(currentAscending ? "desc" : "asc");

      sortTableByColumn(tableId, columnIndex, !currentAscending);
    });
  });