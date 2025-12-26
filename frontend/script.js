const API_URL = 'http://127.0.0.1:5000/api';

const travelForm = document.getElementById('travelForm');
const resultsSection = document.getElementById('resultsSection');
const loadingSpinner = document.getElementById('loadingSpinner');
const itineraryContent = document.getElementById('itineraryContent');
const errorMessage = document.getElementById('errorMessage');
const submitBtn = travelForm.querySelector('.submit-btn');
const exportPdfBtn = document.getElementById('exportPdfBtn');

let currentTripData = null;
let currentItinerary = null;

travelForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        source: document.getElementById('source').value.trim(),
        destination: document.getElementById('destination').value.trim(),
        dates: document.getElementById('dates').value.trim(),
        travelers: parseInt(document.getElementById('travelers').value),
        interests: document.getElementById('interests').value.trim()
    };

    if (!validateForm(formData)) {
        showError('Please fill in all fields correctly');
        return;
    }

    await generateItinerary(formData);
});

exportPdfBtn.addEventListener('click', async () => {
    if (!currentTripData || !currentItinerary) {
        showError('No itinerary to export');
        return;
    }
    
    await exportToPDF();
});

function validateForm(data) {
    return data.source && 
           data.destination && 
           data.dates && 
           data.travelers > 0 && 
           data.interests;
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    resultsSection.style.display = 'none';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

async function generateItinerary(formData) {
    try {
        errorMessage.style.display = 'none';
        resultsSection.style.display = 'block';
        loadingSpinner.style.display = 'flex';
        exportPdfBtn.style.display = 'none';
        itineraryContent.innerHTML = '';
        submitBtn.disabled = true;

        const response = await fetch(`${API_URL}/generate-itinerary`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            loadingSpinner.style.display = 'none';
            currentTripData = formData;
            currentItinerary = data.itinerary;
            exportPdfBtn.style.display = 'block';
            displayItinerary(data.itinerary);
        } else {
            throw new Error(data.error || 'Failed to generate itinerary');
        }
    } catch (error) {
        loadingSpinner.style.display = 'none';
        showError(`Error: ${error.message}. Make sure the backend is running on http://127.0.0.1:5000`);
        resultsSection.style.display = 'none';
    } finally {
        submitBtn.disabled = false;
    }
}

function displayItinerary(content) {
    itineraryContent.textContent = content;
    itineraryContent.innerHTML = itineraryContent.innerHTML
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/###\s(.+?)(?=\n|$)/g, '<h3>$1</h3>')
        .replace(/##\s(.+?)(?=\n|$)/g, '<h2>$1</h2>')
        .replace(/^#\s(.+?)(?=\n|$)/gm, '<h1>$1</h1>')
        .replace(/\n/g, '<br>');
}

async function exportToPDF() {
    try {
        exportPdfBtn.disabled = true;
        exportPdfBtn.textContent = '📥 Generating PDF...';
        
        const exportData = {
            ...currentTripData,
            itinerary: currentItinerary
        };
        
        const response = await fetch(`${API_URL}/export-pdf`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(exportData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `travel_plan_${currentTripData.destination}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
    } catch (error) {
        showError(`Error exporting PDF: ${error.message}`);
    } finally {
        exportPdfBtn.disabled = false;
        exportPdfBtn.textContent = '📥 Download PDF';
    }
}

window.addEventListener('load', () => {
    checkBackendHealth();
});

async function checkBackendHealth() {
    try {
        const response = await fetch(`${API_URL}/health`);
        if (!response.ok) {
            console.warn('Backend health check failed');
        }
    } catch (error) {
        console.warn('Backend is not running on http://127.0.0.1:5000', error);
    }
}
