"""
Campaign state management - save/load campaigns as JSON files.
"""
import json
import os
import re
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime


class CampaignManager:
    """Manage D&D campaign persistence."""

    def __init__(self, campaigns_dir: str = "campaigns"):
        """
        Initialize campaign manager.

        Args:
            campaigns_dir: Directory to store campaign JSON files
        """
        self.campaigns_dir = Path(campaigns_dir)
        self.campaigns_dir.mkdir(exist_ok=True)

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_-]+', '-', text)
        text = re.sub(r'^-+|-+$', '', text)
        return text[:50]  # Limit length

    def create_campaign(self, campaign_data: Dict, campaign_id: Optional[str] = None) -> str:
        """
        Create and save a new campaign.

        Args:
            campaign_data: Campaign data dictionary
            campaign_id: Optional campaign ID (generates one if not provided)

        Returns:
            Campaign ID
        """
        if not campaign_id:
            # Generate descriptive ID from title
            title = campaign_data.get("title", "Untitled Campaign")
            slug = self._slugify(title)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            campaign_id = f"{slug}_{timestamp}"

        campaign_data["id"] = campaign_id
        campaign_data["created_at"] = datetime.now().isoformat()
        campaign_data["updated_at"] = datetime.now().isoformat()

        self._save_campaign(campaign_id, campaign_data)
        return campaign_id

    def get_campaign(self, campaign_id: str) -> Optional[Dict]:
        """
        Load a campaign by ID.

        Args:
            campaign_id: Campaign ID

        Returns:
            Campaign data or None if not found
        """
        campaign_file = self.campaigns_dir / f"{campaign_id}.json"

        if not campaign_file.exists():
            return None

        with open(campaign_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def update_campaign(self, campaign_id: str, campaign_data: Dict) -> bool:
        """
        Update an existing campaign.

        Args:
            campaign_id: Campaign ID
            campaign_data: Updated campaign data

        Returns:
            True if successful, False if campaign not found
        """
        if not self.campaign_exists(campaign_id):
            return False

        campaign_data["id"] = campaign_id
        campaign_data["updated_at"] = datetime.now().isoformat()

        self._save_campaign(campaign_id, campaign_data)
        return True

    def campaign_exists(self, campaign_id: str) -> bool:
        """
        Check if a campaign exists.

        Args:
            campaign_id: Campaign ID

        Returns:
            True if campaign exists
        """
        campaign_file = self.campaigns_dir / f"{campaign_id}.json"
        return campaign_file.exists()

    def list_campaigns(self) -> list:
        """
        List all campaign IDs.

        Returns:
            List of campaign IDs
        """
        campaigns = []
        for file in self.campaigns_dir.glob("*.json"):
            campaigns.append(file.stem)
        return sorted(campaigns, reverse=True)

    def list_campaigns_with_details(self) -> List[Dict]:
        """
        List all campaigns with their title and metadata.

        Returns:
            List of campaign summaries (id, title, created_at, updated_at, images_count, updates_count)
        """
        summaries = []
        for file in self.campaigns_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    campaign = json.load(f)
                    summaries.append({
                        "id": campaign.get("id", file.stem),
                        "title": campaign.get("title", "Untitled Campaign"),
                        "setting": campaign.get("setting", "")[:100] + "..." if len(campaign.get("setting", "")) > 100 else campaign.get("setting", ""),
                        "created_at": campaign.get("created_at", ""),
                        "updated_at": campaign.get("updated_at", ""),
                        "images_count": len(campaign.get("images", [])),
                        "updates_count": len(campaign.get("updates", []))
                    })
            except Exception as e:
                print(f"Error loading campaign {file}: {e}")
                continue

        # Sort by updated_at (most recent first)
        summaries.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return summaries

    def add_image_to_campaign(self, campaign_id: str, image_filename: str, objects: Dict[str, int]) -> bool:
        """
        Add image metadata to a campaign.
        Note: The actual image file is deleted after processing to save space.

        Args:
            campaign_id: Campaign ID
            image_filename: Name of the uploaded image (not full path, as file is deleted)
            objects: Detected objects from the image

        Returns:
            True if successful
        """
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return False

        campaign.setdefault("images", []).append({
            "filename": image_filename,
            "objects": objects,
            "uploaded_at": datetime.now().isoformat()
        })

        return self.update_campaign(campaign_id, campaign)

    def _save_campaign(self, campaign_id: str, campaign_data: Dict):
        """Save campaign data to JSON file."""
        campaign_file = self.campaigns_dir / f"{campaign_id}.json"

        with open(campaign_file, 'w', encoding='utf-8') as f:
            json.dump(campaign_data, f, indent=2, ensure_ascii=False)
