"""
D&D Campaign generation using Groq LLM API.
"""
import os
import json
from typing import List, Dict, Optional
from groq import Groq


class CampaignGenerator:
    """Generate and update D&D campaigns using Groq LLM."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the campaign generator.

        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"  # Fast and creative

    def generate_initial_campaign(self, objects: Dict[str, int], image_description: str = "") -> Dict:
        """
        Generate a new D&D campaign based on detected objects.

        Args:
            objects: Dictionary of detected objects and their counts
            image_description: Optional description of the image

        Returns:
            Campaign data including story, NPCs, locations, and quests
        """
        objects_list = [f"{count} {obj}" for obj, count in objects.items()]
        objects_str = ", ".join(objects_list)

        prompt = f"""You are a creative Dungeon Master creating a D&D campaign.

Based on these objects detected in an image: {objects_str}
{f"Image context: {image_description}" if image_description else ""}

Create an engaging D&D campaign with the following structure:

1. **Campaign Title**: A catchy, evocative title
2. **Setting**: Describe the world/location (2-3 sentences)
3. **Main Story Hook**: The central conflict or mystery (2-3 sentences)
4. **NPCs**: 2-3 key non-player characters with names, roles, and personalities
5. **Locations**: 2-3 important places in the campaign
6. **Initial Quest**: The first quest/objective for the players
7. **Potential Encounters**: 2-3 possible combat or social encounters

Be creative and weave the detected objects naturally into the campaign narrative.

Return your response in valid JSON format with these exact keys:
{{
  "title": "Campaign Title",
  "setting": "Setting description",
  "story_hook": "Main story hook",
  "npcs": [
    {{"name": "NPC Name", "role": "Their role", "personality": "Brief personality"}}
  ],
  "locations": [
    {{"name": "Location Name", "description": "Brief description"}}
  ],
  "initial_quest": "Quest description",
  "encounters": [
    {{"type": "combat or social", "description": "Encounter description"}}
  ]
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a creative Dungeon Master. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=2048
        )

        campaign_json = response.choices[0].message.content

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in campaign_json:
            campaign_json = campaign_json.split("```json")[1].split("```")[0].strip()
        elif "```" in campaign_json:
            campaign_json = campaign_json.split("```")[1].split("```")[0].strip()

        campaign = json.loads(campaign_json)
        campaign["images"] = []
        campaign["updates"] = []

        return campaign

    def update_campaign(self, existing_campaign: Dict, new_objects: Dict[str, int], image_description: str = "") -> Dict:
        """
        Update an existing campaign with new objects from a new image.

        Args:
            existing_campaign: The current campaign data
            new_objects: Dictionary of newly detected objects
            image_description: Optional description of the new image

        Returns:
            Updated campaign data
        """
        objects_list = [f"{count} {obj}" for obj, count in new_objects.items()]
        objects_str = ", ".join(objects_list)

        campaign_summary = f"""
Current Campaign: {existing_campaign.get('title', 'Untitled')}
Setting: {existing_campaign.get('setting', 'Unknown')}
Story: {existing_campaign.get('story_hook', 'Unknown')}
Recent Updates: {len(existing_campaign.get('updates', []))}
"""

        prompt = f"""You are a Dungeon Master updating an ongoing D&D campaign.

{campaign_summary}

A new image has been uploaded with these objects: {objects_str}
{f"Image context: {image_description}" if image_description else ""}

Based on these new elements, create a campaign update that:
1. Adds a new story development or plot twist
2. Optionally introduces 1-2 new NPCs or locations if relevant
3. Provides a new quest or objective
4. Suggests 1-2 new encounters

Weave the new objects naturally into the existing campaign narrative.

Return your response in valid JSON format:
{{
  "story_development": "New plot development",
  "new_npcs": [
    {{"name": "NPC Name", "role": "Their role", "personality": "Brief personality"}}
  ],
  "new_locations": [
    {{"name": "Location Name", "description": "Brief description"}}
  ],
  "new_quest": "New quest description",
  "new_encounters": [
    {{"type": "combat or social", "description": "Encounter description"}}
  ]
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a creative Dungeon Master. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1536
        )

        update_json = response.choices[0].message.content

        # Extract JSON from response
        if "```json" in update_json:
            update_json = update_json.split("```json")[1].split("```")[0].strip()
        elif "```" in update_json:
            update_json = update_json.split("```")[1].split("```")[0].strip()

        update = json.loads(update_json)

        # Merge update into existing campaign
        if "new_npcs" in update and update["new_npcs"]:
            existing_campaign.setdefault("npcs", []).extend(update["new_npcs"])

        if "new_locations" in update and update["new_locations"]:
            existing_campaign.setdefault("locations", []).extend(update["new_locations"])

        if "new_encounters" in update and update["new_encounters"]:
            existing_campaign.setdefault("encounters", []).extend(update["new_encounters"])

        # Add update to history
        existing_campaign.setdefault("updates", []).append({
            "story_development": update.get("story_development", ""),
            "new_quest": update.get("new_quest", ""),
            "objects": new_objects
        })

        return existing_campaign
