// Wait until both DOM and ADMIN_DATA are ready
document.addEventListener("DOMContentLoaded", () => {
    // Sidebar switching
    document.querySelectorAll('.sidebar ul li a').forEach(link => {
      link.addEventListener('click', e => {
        e.preventDefault();
        const target = link.getAttribute('data-target');
        document.querySelectorAll('.content-section').forEach(sec => sec.style.display = 'none');
        document.getElementById(`content-${target}`).style.display = 'block';
        document.querySelector('.sidebar ul li a.active').classList.remove('active');
        link.classList.add('active');
      });
    });
  
    // Charts (requires Chart.js loaded separately)
    const { chartLabels, chartData, awardLabels, awardCounts, awardColors } = window.ADMIN_DATA;
  
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
  
    new Chart(document.getElementById('chart-hours-by-group'), {
      type: 'bar',
      data: {
        labels: ['Group A','Group B','Group C','Group D'],
        datasets: [{ label: 'Approved Hours', data: [120, 90, 150, 80] }]
      },
      options: { responsive: true, maintainAspectRatio: false }
    });
  
    new Chart(document.getElementById('chart-award-distribution'), {
      type: 'pie',
      data: {
        labels: awardLabels,
        datasets: [{ data: awardCounts, backgroundColor: awardColors }]
      },
      options: { responsive: true, maintainAspectRatio: false }
    });
  
    // DataTables
    if (window.jQuery && $.fn.DataTable) {
      $('#studentsTable').DataTable({ pageLength: 10 });
    }
  
    // Pagination + Sorting + Search for submissionsTable
    const rows = Array.from(document.querySelectorAll("#submissionsTable tbody tr"));
    const rowsPerPage = 7;
    let currentPage = 1;
    let filteredRows = [...rows];
    let currentSortedColumn = null;
    let currentSortAsc = true;
  
    const prevBtn = document.getElementById("prevPage"),
          nextBtn = document.getElementById("nextPage"),
          pageIndicator = document.getElementById("pageIndicator"),
          searchInput = document.getElementById("searchInput");
  
    function showPage(page) {
      const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
      const start = (page - 1) * rowsPerPage,
            end = start + rowsPerPage;
      rows.forEach(r => r.style.display = 'none');
      filteredRows.slice(start, end).forEach(r => r.style.display = '');
      pageIndicator.textContent = `Page ${page}`;
      prevBtn.disabled = page === 1;
      nextBtn.disabled = page === totalPages || totalPages === 0;
    }
  
    function sortRows(column) {
      filteredRows.sort((a,b) => {
        let aText = a.cells[column].innerText.trim(),
            bText = b.cells[column].innerText.trim();
        if (column === 3) {
          return currentSortAsc
            ? new Date(aText) - new Date(bText)
            : new Date(bText) - new Date(aText);
        }
        const aNum = parseFloat(aText), bNum = parseFloat(bText);
        if (!isNaN(aNum) && !isNaN(bNum)) {
          return currentSortAsc ? aNum - bNum : bNum - aNum;
        }
        return currentSortAsc ? aText.localeCompare(bText) : bText.localeCompare(aText);
      });
    }
  
    // Attach header sorting
    document.querySelectorAll(".sortable").forEach(header => {
      header.addEventListener('click', () => {
        const col = parseInt(header.dataset.column, 10);
        if (currentSortedColumn === col) currentSortAsc = !currentSortAsc;
        else { currentSortedColumn = col; currentSortAsc = true; }
        document.querySelectorAll(".sortable").forEach(h => h.classList.remove('asc','desc'));
        header.classList.add(currentSortAsc ? 'asc':'desc');
        sortRows(col);
        showPage(currentPage);
      });
    });
  
    // Search filtering
    searchInput.addEventListener('input', () => {
      const term = searchInput.value.toLowerCase();
      filteredRows = rows.filter(r => {
        const name = r.cells[0].innerText.toLowerCase(),
              date = r.cells[3].innerText.toLowerCase(),
              grp  = r.cells[5].innerText.toLowerCase();
        return name.includes(term) || date.includes(term) || grp.includes(term);
      });
      currentPage = 1;
      showPage(currentPage);
    });
  
    prevBtn.addEventListener('click', () => { if (currentPage>1) showPage(--currentPage); });
    nextBtn.addEventListener('click', () => {
      const totalPages = Math.ceil(filteredRows.length/rowsPerPage);
      if (currentPage<totalPages) showPage(++currentPage);
    });
  
    // Default sort by date desc
    currentSortedColumn = 3; currentSortAsc = false;
    sortRows(3);
    showPage(1);
  
    // Row click → review modal
    let modalEdited = false;
    document.querySelectorAll('.submission-row').forEach(row => {
      row.addEventListener('click', () => {
        const attrs = row.dataset;
        document.getElementById('modal-student').innerText = `${attrs.studentName} (${attrs.userId})`;
        document.getElementById('modal-activity').innerText = attrs.description;
        document.getElementById('modal-hours').innerText = attrs.hours;
        document.getElementById('modal-date').innerText = attrs.formattedDate || attrs.date;
        document.getElementById('modal-status').innerText = attrs.statusLabel;
        document.getElementById('modal-group').innerText = attrs.group || "N/A";
        document.getElementById('modal-log-time').innerText = attrs.formattedLogTime || "N/A";
        ['approve','reject','edit'].forEach(act => {
          document.getElementById(`${act}-log-id`).value = attrs.id;
        });
        document.getElementById('modal-student-img').src = attrs.pictureUrl || '/static/default-profile.png';
        document.getElementById('reviewModal').style.display = 'block';
      });
    });
  
    document.getElementById('reviewModal').addEventListener('click', e => {
      if (e.target === e.currentTarget) e.currentTarget.style.display = 'none';
    });
    window.closeModal = () => {
      document.getElementById('reviewModal').style.display = 'none';
      if (modalEdited) window.location.reload();
    };
  
    // Inline edit & save
    function saveEdits() {
      const logId = document.getElementById('edit-log-id').value;
      let rawDate = document.getElementById('modal-date').innerText.trim(),
          d = new Date(rawDate),
          formatted = `${('0'+d.getDate()).slice(-2)}-${('0'+(d.getMonth()+1)).slice(-2)}-${d.getFullYear()}`;
      const payload = {
        log_id: logId,
        description: document.getElementById('modal-activity').innerText.trim(),
        hours: document.getElementById('modal-hours').innerText.trim(),
        date: formatted
      };
      fetch('/update-log-field', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      }).then(r=>r.json()).then(() => modalEdited=true);
    }
  
    window.makeEditable = id => {
      const el = document.getElementById(id);
      el.contentEditable = true; el.classList.add('editing'); el.focus();
      const onKey = e => e.key==='Enter' && (e.preventDefault(), el.blur());
      const onBlur = () => {
        el.contentEditable=false; el.classList.remove('editing');
        el.removeEventListener('keydown', onKey);
        el.removeEventListener('blur', onBlur);
        saveEdits();
      };
      el.addEventListener('keydown', onKey);
      el.addEventListener('blur', onBlur);
    };
  });