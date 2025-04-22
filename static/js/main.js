// Form submission handler
document.getElementById('newsForm').addEventListener('submit', function() {
    document.getElementById('loadingIndicator').style.display = 'block';
    document.getElementById('results').style.display = 'none';
    document.getElementById('fetchBtn').disabled = true;
});

// Initialize date inputs
window.addEventListener('load', function() {
    const today = new Date();
    const lastWeek = new Date(today);
    lastWeek.setDate(today.getDate() - 7);
    
    const formatDate = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };
    
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    
    if (!startDateInput.value) {
        startDateInput.value = formatDate(lastWeek);
    }
    
    if (!endDateInput.value) {
        endDateInput.value = formatDate(today);
    }
});

// Theme toggle functionality
document.getElementById('theme-toggle').addEventListener('click', function() {
    document.body.classList.toggle('dark-mode');
    const icon = this.querySelector('i');
    
    if (document.body.classList.contains('dark-mode')) {
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
        localStorage.setItem('theme', 'dark');
    } else {
        icon.classList.remove('fa-sun');
        icon.classList.add('fa-moon');
        localStorage.setItem('theme', 'light');
    }
});

// Check for saved theme preference
window.addEventListener('DOMContentLoaded', function() {
    const savedTheme = localStorage.getItem('theme');
    const themeToggle = document.getElementById('theme-toggle');
    
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        themeToggle.querySelector('i').classList.remove('fa-moon');
        themeToggle.querySelector('i').classList.add('fa-sun');
    }
});