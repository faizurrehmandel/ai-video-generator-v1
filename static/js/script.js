/**
 * @file script.js
 * @description Frontend JavaScript for the AI Video Generator application.
 * This script handles form submission, communicates with the backend API to
 * generate a video, displays loading states, and presents the final
- * video and a download link to the user.
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element References ---
    const videoForm = document.getElementById('video-form');
    const topicInput = document.getElementById('topic');
    const generateBtn = document.getElementById('generate-btn');
    const loader = document.getElementById('loader');
    const statusMessage = document.getElementById('status-message');
    const resultContainer = document.getElementById('result-container');
    const videoPlayer = document.getElementById('video-player');
    const videoSource = document.getElementById('video-source');
    const downloadLink = document.getElementById('download-link');

    /**
     * Handles the video generation form submission.
     * @param {Event} event - The form submission event.
     */
    const handleFormSubmit = async (event) => {
        event.preventDefault(); // Prevent the default form submission behavior

        const topic = topicInput.value.trim();
        if (!topic) {
            updateStatus('Please enter a topic to generate a video.', 'error');
            return;
        }

        // --- Start Loading State ---
        setLoadingState(true);
        updateStatus('Initializing video generation... This may take a few minutes.', 'info');

        try {
            // --- API Request to Backend ---
            const response = await fetch('/generate-video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic: topic }),
            });

            const result = await response.json();

            if (!response.ok) {
                // Throw an error to be caught by the catch block
                throw new Error(result.error || `Server responded with status: ${response.status}`);
            }

            // --- Handle Successful Response ---
            if (result.success && result.video_url) {
                displayVideoResult(result.video_url);
                updateStatus('Video generated successfully!', 'success');
            } else {
                // Handle cases where the request was successful but the operation failed
                throw new Error(result.error || 'An unexpected error occurred.');
            }

        } catch (error) {
            console.error('Video Generation Error:', error);
            updateStatus(`Error: ${error.message}`, 'error');
            resultContainer.style.display = 'none'; // Hide any previous results on new error
        } finally {
            // --- End Loading State ---
            setLoadingState(false);
        }
    };

    /**
     * Toggles the UI into a loading or non-loading state.
     * @param {boolean} isLoading - True to enter loading state, false to exit.
     */
    const setLoadingState = (isLoading) => {
        if (isLoading) {
            generateBtn.disabled = true;
            generateBtn.textContent = 'Generating...';
            loader.style.display = 'block';
            resultContainer.style.display = 'none'; // Hide previous results
        } else {
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Video';
            loader.style.display = 'none';
        }
    };

    /**
     * Updates the status message displayed to the user.
     * @param {string} message - The message to display.
     * @param {'info'|'success'|'error'} type - The type of message, for styling.
     */
    const updateStatus = (message, type) => {
        statusMessage.textContent = message;
        statusMessage.className = `status-message ${type}`; // Apply CSS class for color
    };

    /**
     * Displays the generated video and provides a download link.
     * @param {string} videoUrl - The URL of the generated video file.
     */
    const displayVideoResult = (videoUrl) => {
        // Set the source for the video player and load it
        videoSource.src = videoUrl;
        videoPlayer.load(); // Important to load the new source

        // Set the href for the download link
        downloadLink.href = videoUrl;
        downloadLink.download = `ai_video_${Date.now()}.mp4`; // Suggest a filename

        // Make the result container visible
        resultContainer.style.display = 'block';
    };

    // --- Attach Event Listeners ---
    if (videoForm) {
        videoForm.addEventListener('submit', handleFormSubmit);
    } else {
        console.error('Error: The video form with ID "video-form" was not found.');
    }
});