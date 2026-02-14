// D&D Campaign Generator - Frontend

let selectedFile = null;
let currentCampaignId = null;

// DOM Elements
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const campaignSection = document.getElementById('campaignSection');
const imageDescription = document.getElementById('imageDescription');
const campaignSelect = document.getElementById('campaignSelect');

// Campaign mode radio buttons
const campaignModeRadios = document.querySelectorAll('input[name="campaignMode"]');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadCampaignsList();
});

function setupEventListeners() {
    // Upload box click
    uploadBox.addEventListener('click', () => fileInput.click());

    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFileSelect(e.target.files[0]);
    });

    // Drag and drop
    uploadBox.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadBox.classList.add('dragover');
    });

    uploadBox.addEventListener('dragleave', () => {
        uploadBox.classList.remove('dragover');
    });

    uploadBox.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadBox.classList.remove('dragover');
        handleFileSelect(e.dataTransfer.files[0]);
    });

    // Upload button
    uploadBtn.addEventListener('click', uploadImage);

    // Campaign mode change
    campaignModeRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            campaignSelect.disabled = e.target.value === 'new';
        });
    });
}

function handleFileSelect(file) {
    if (!file) return;

    if (!file.type.startsWith('image/')) {
        alert('Please select an image file');
        return;
    }

    selectedFile = file;
    uploadBox.querySelector('.upload-text').textContent = `Selected: ${file.name}`;
    uploadBtn.disabled = false;
}

async function loadCampaignsList() {
    try {
        const response = await fetch('/api/campaigns');
        const data = await response.json();

        campaignSelect.innerHTML = '<option value="">Select a campaign...</option>';

        data.campaigns.forEach(campaignId => {
            const option = document.createElement('option');
            option.value = campaignId;
            option.textContent = campaignId;
            campaignSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading campaigns:', error);
    }
}

async function uploadImage() {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('image', selectedFile);
    formData.append('description', imageDescription.value);

    // Check campaign mode
    const campaignMode = document.querySelector('input[name="campaignMode"]:checked').value;
    if (campaignMode === 'update' && campaignSelect.value) {
        formData.append('campaign_id', campaignSelect.value);
    }

    // Show loading
    loadingIndicator.style.display = 'block';
    uploadBtn.disabled = true;

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        const data = await response.json();

        currentCampaignId = data.campaign_id;
        displayCampaign(data.campaign, data.objects, data.updated);

        // Reload campaigns list
        await loadCampaignsList();

        // Reset form
        selectedFile = null;
        fileInput.value = '';
        imageDescription.value = '';
        uploadBox.querySelector('.upload-text').textContent = 'Drag & drop an image here';

    } catch (error) {
        console.error('Error:', error);
        alert('Failed to generate campaign. Make sure GROQ_API_KEY is set.');
    } finally {
        loadingIndicator.style.display = 'none';
        uploadBtn.disabled = false;
    }
}

function displayCampaign(campaign, objects, isUpdate) {
    // Show campaign section
    campaignSection.style.display = 'block';
    campaignSection.scrollIntoView({ behavior: 'smooth' });

    // Campaign header
    document.getElementById('campaignTitle').textContent = campaign.title;
    document.getElementById('campaignId').textContent = `ID: ${campaign.id}`;

    // Setting & Story Hook
    document.getElementById('campaignSetting').textContent = campaign.setting;
    document.getElementById('campaignStoryHook').textContent = campaign.story_hook;

    // NPCs
    const npcsContainer = document.getElementById('campaignNPCs');
    npcsContainer.innerHTML = '';
    campaign.npcs.forEach(npc => {
        const npcDiv = document.createElement('div');
        npcDiv.className = 'npc-item';
        npcDiv.innerHTML = `
            <h4>${npc.name} - ${npc.role}</h4>
            <p>${npc.personality}</p>
        `;
        npcsContainer.appendChild(npcDiv);
    });

    // Locations
    const locationsContainer = document.getElementById('campaignLocations');
    locationsContainer.innerHTML = '';
    campaign.locations.forEach(location => {
        const locationDiv = document.createElement('div');
        locationDiv.className = 'location-item';
        locationDiv.innerHTML = `
            <h4>${location.name}</h4>
            <p>${location.description}</p>
        `;
        locationsContainer.appendChild(locationDiv);
    });

    // Quest
    const questText = campaign.initial_quest ||
                      (campaign.updates && campaign.updates.length > 0 ?
                       campaign.updates[campaign.updates.length - 1].new_quest :
                       'No quest available');
    document.getElementById('campaignQuest').textContent = questText;

    // Encounters
    const encountersContainer = document.getElementById('campaignEncounters');
    encountersContainer.innerHTML = '';
    campaign.encounters.forEach(encounter => {
        const encounterDiv = document.createElement('div');
        encounterDiv.className = 'encounter-item';
        encounterDiv.innerHTML = `
            <h4>${encounter.type.toUpperCase()}</h4>
            <p>${encounter.description}</p>
        `;
        encountersContainer.appendChild(encounterDiv);
    });

    // Updates (if any)
    if (campaign.updates && campaign.updates.length > 0) {
        const updatesCard = document.getElementById('updatesCard');
        updatesCard.style.display = 'block';

        const updatesContainer = document.getElementById('campaignUpdates');
        updatesContainer.innerHTML = '';

        campaign.updates.forEach((update, index) => {
            const updateDiv = document.createElement('div');
            updateDiv.className = 'update-item';
            updateDiv.innerHTML = `
                <p><strong>Update ${index + 1}:</strong> ${update.story_development}</p>
                ${update.new_quest ? `<p><strong>New Quest:</strong> ${update.new_quest}</p>` : ''}
            `;
            updatesContainer.appendChild(updateDiv);
        });
    }

    // Detected Objects
    const objectsContainer = document.getElementById('detectedObjects');
    objectsContainer.innerHTML = '';
    const objectTags = document.createElement('div');
    objectTags.className = 'object-tags';

    Object.entries(objects).forEach(([obj, count]) => {
        const tag = document.createElement('span');
        tag.className = 'object-tag';
        tag.textContent = `${obj} (${count})`;
        objectTags.appendChild(tag);
    });

    objectsContainer.appendChild(objectTags);
}
