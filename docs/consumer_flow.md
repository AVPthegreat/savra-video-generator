# Savra Video Generator Consumer Flow

This document outlines the proposed User Experience (UX) and User Interface (UI) journey for consumers using the Savra Video Generator platform. The goal is to provide a seamless, intuitive, and frictionless experience from content input to the final video download, utilizing our premium frontend architecture, while strictly protecting backend resources.

---

## 1. Landing Page (The Entry Point)
The consumer's journey begins on the Savra Video Generator Landing Page, which introduces the platform's capabilities with a premium aesthetic.

*   **Key Elements:** High-impact typography, glassmorphism design elements, and a subtle animated background.
*   **Call to Action (CTA):** A prominent **"Start Creating"** or **"Launch Studio"** button that directs the user to the Consumer Input View.
*   *Note for Admins:* The admin login will be moved to a discrete location (e.g., footer) to prioritize the consumer experience.

---

## 2. Input View (Content Submission)
Once the consumer clicks the CTA, they are taken to the Input View, where they provide the source material for their video.

*   **Content Input Methods:**
    *   **Text Field:** A sleek, modern text area for pasting scripts or raw notes.
    *   **File Upload:** A drag-and-drop zone accepting `.txt`, `.pdf`, and `.docx` files.
*   **Configuration Options:**
    *   **Scene Count:** A simple slider allowing the user to request a specific number of scenes. *Note: Unauthenticated consumer limits will be strictly capped at a low number (e.g., 3 scenes) to prevent abuse.*
*   **Action:** Clicking **"Generate Animation"** triggers the backend `/upload` (if file) and `/generate/async` endpoints.

---

## 3. Processing View (The Magic Happens)
Video generation involves complex LLM orchestration and rendering. 

*   **Visual Feedback:** A sophisticated loading animation aligns with our premium design system.
*   **Expected Duration:** The typical process takes between **10 to 60 seconds**, depending on the scene count and infrastructure load.
*   **Status Updates:** The frontend continuously polls the `/jobs/{job_id}` endpoint and updates the UI with dynamic status messages (*"Analyzing document...", "Choreographing scenes...", "Rendering whiteboard..."*).
*   **Timeout Handling & Background Processing:**
    *   If a job exceeds the expected duration (e.g., >90 seconds), the UI will gracefully transition to a "Taking longer than expected" state.
    *   **Asynchronous Option:** The UI will provide a session link or an option to enter an email (if implemented) so the user can leave the page and be notified/return later without keeping the browser tab open.

---

## 4. Result View (Playback & Download)
Once the backend completes the render, the UI seamlessly transitions to the Result View.

*   **Video Player:** A custom HTML5 video player prominently displays the final `.mp4` whiteboard animation.
*   **Consumer Actions:**
    *   **Download:** A clear button to save the MP4 artifact directly to their device.
    *   **Create Another:** A button to reset the flow and return to the Input View.

---

## 5. Edge Cases & Failure Handling
To ensure a robust UX, the frontend must explicitly handle the following failure states with clear, user-friendly messaging and recovery options:

*   **Empty / Invalid Input:** 
    *   *Trigger:* User submits without text, or text is gibberish/too short.
    *   *Action:* Client-side validation prevents submission. Server-side validation returns a `400 Bad Request`. UI highlights the text box and prompts for valid content.
*   **Upload Fails:** 
    *   *Trigger:* Network drop, unsupported file type, or file exceeds `MAX_UPLOAD_MB`.
    *   *Action:* UI displays a specific error ("File too large" or "Unsupported format") and falls back to requesting raw text input.
*   **LLM Fails (Gemini API):** 
    *   *Trigger:* Gemini API quota limits, context length exceeded, or upstream service outages.
    *   *Action:* Job status marks as `failed`. UI displays: *"Our AI director is currently overwhelmed. Please try again in a few moments or try a shorter text."*
*   **Render Timeout:** 
    *   *Trigger:* Remotion headless browser crash or FFmpeg stitch failure.
    *   *Action:* UI detects the backend failure state and prompts the user to retry the generation, automatically submitting the cached text.
*   **Job Stuck in Processing:** 
    *   *Trigger:* Polling returns `running` indefinitely (e.g., worker crashed without updating DB).
    *   *Action:* If polling continues beyond a hard limit (e.g., 3 minutes), the UI declares a timeout, stops polling, and provides a "Report Issue" or "Retry" action.

---

## 6. Security & Cost Management (Public API Protection)
Opening generative pipelines to public consumers introduces a severe risk of **cost explosion** (draining LLM credits and cloud compute). Simply bypassing the admin token is unacceptable. To safely expose the API, the following infrastructure must be implemented:

1.  **Abuse Detection (Bot Prevention):**
    *   Integrate **reCAPTCHA v3** or **Cloudflare Turnstile** on the frontend. The `/generate/async` endpoint must validate this token before accepting the job, preventing automated scripts from burning credits.
2.  **Strict Rate Limiting:**
    *   Implement Redis-backed rate limiting.
    *   **Per IP Limit:** e.g., Maximum 2 generation requests per hour.
    *   **Per Session Limit:** Use browser fingerprinting or HTTP-only cookies to enforce quotas.
3.  **Request Quotas & Hard Caps:**
    *   Set daily budget alerts and hard caps at the Google Cloud API Gateway/Billing level. If the daily budget is hit, the API immediately returns `429 Too Many Requests` or `503 Service Unavailable`, and the UI displays a "Daily Limit Reached" message.
4.  **Resource Throttling for Guests:**
    *   Unauthenticated consumers should be heavily constrained compared to Admins.
    *   Max input text length: Severely reduced.
    *   Max scene count: Locked to 2 or 3 scenes max to minimize LLM context windows and render times.
