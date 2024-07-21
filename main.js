console.log('Hello')

const formChat = document.getElementById('formChat');

formChat.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const formData = new FormData(formChat);
    const data = new URLSearchParams();
    for (const pair of formData) {
        data.append(pair[0], pair[1]);
    }

    fetch('/message', {
        method: 'POST',
        body: data
    }).then(response => {
        if (response.ok) {
            console.log('Message sent successfully');
        } else {
            console.error('Error sending message');
        }
    }).catch(error => {
        console.error('Error:', error);
    });
});
