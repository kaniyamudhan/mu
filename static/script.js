document.addEventListener('DOMContentLoaded', function() {
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');

    sendBtn.addEventListener('click', sendMessage);

    userInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const messageText = userInput.value.trim();
        if (messageText === '') return;

        addMessage('user', messageText);
        userInput.value = '';

        fetch('/get_response', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ message: messageText, user_id: 'user123' })
        })
        .then(response => response.json())
        .then(data => {
            addMessage('bot', data.response);
            chatBox.scrollTop = chatBox.scrollHeight;
        })
        .catch(error => console.error('Error:', error));
    }

    function addMessage(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', sender);
        
        const messageText = document.createElement('div');
        messageText.classList.add('message-text');
        messageText.textContent = message;

        messageElement.appendChild(messageText);
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});
