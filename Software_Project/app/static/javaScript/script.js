document.getElementById('registerForm').addEventListener('submit', function (event) {
    event.preventDefault();

    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    fetch('/api/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            email: email,
            password: password
        }),
    })
        .then(response => response.json())
        .then(data => {
            console.log('Success:', data);
            alert('Registration Successful!');
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('Registration Failed');
        });
});
