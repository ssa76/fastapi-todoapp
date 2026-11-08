// Shared page scripts (loaded by templates/layout.html with `defer`, so the DOM is ready).
// Each section only runs on the page that has its form.

const TODOS_PAGE = '/todos-page';
const LOGIN_PAGE = '/login';

// Add Todo
const todoForm = document.getElementById('todoForm');
if (todoForm) {
    todoForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        const data = formValues(event.target);

        const response = await apiFetch('/todos', {
            method: 'POST',
            body: {
                title: data.title,
                description: data.description,
                priority: parseInt(data.priority),
                complete: false
            }
        });
        if (response) window.location.href = TODOS_PAGE;
    });
}

// Edit / Delete Todo
const editTodoForm = document.getElementById('editTodoForm');
if (editTodoForm) {
    // The page URL is /edit-todos-page/<id>.
    const todoId = window.location.pathname.split('/').pop();

    editTodoForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        const data = formValues(event.target);

        const response = await apiFetch(`/todos/${todoId}`, {
            method: 'PUT',
            body: {
                title: data.title,
                description: data.description,
                priority: parseInt(data.priority),
                complete: data.complete === 'on'
            }
        });
        if (response) window.location.href = TODOS_PAGE;
    });

    const deleteButton = document.getElementById('deleteButton');
    if (deleteButton) {
        deleteButton.addEventListener('click', async function () {
            if (!confirm('Delete this todo?')) return;

            const response = await apiFetch(`/todos/${todoId}`, { method: 'DELETE' });
            if (response) window.location.href = TODOS_PAGE;
        });
    }
}

// Login
const loginForm = document.getElementById('loginForm');
if (loginForm) {
    loginForm.addEventListener('submit', async function (event) {
        event.preventDefault();

        try {
            // OAuth2 password flow: form-encoded, not JSON. No token yet, so plain fetch.
            const response = await fetch('/auth/token', {
                method: 'POST',
                body: new URLSearchParams(new FormData(event.target))
            });
            if (!response.ok) {
                alert(`Error: ${errorMessage(await response.json())}`);
                return;
            }
            const data = await response.json();
            // SameSite=Lax: not sent with cross-site POSTs.
            document.cookie = `access_token=${data.access_token}; path=/; SameSite=Lax`;
            window.location.href = TODOS_PAGE;
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        }
    });
}

// Register
const registerForm = document.getElementById('registerForm');
if (registerForm) {
    registerForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        const data = formValues(event.target);

        if (data.password !== data.password2) {
            alert('Passwords do not match');
            return;
        }

        try {
            const response = await fetch('/auth', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: data.email,
                    username: data.username,
                    first_name: data.firstname,
                    last_name: data.lastname,
                    phone_number: data.phone_number.trim() || null, // optional
                    password: data.password
                })
            });
            if (!response.ok) {
                alert(`Error: ${errorMessage(await response.json())}`);
                return;
            }
            window.location.href = LOGIN_PAGE;
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        }
    });
}

// Call the JSON API as the logged-in user. `body` is sent as JSON.
// Returns the response when it's OK; otherwise shows the error and returns null.
// A 401 means the login has expired (or was revoked): log out and go to the login page.
async function apiFetch(url, { method = 'GET', body } = {}) {
    const token = getCookie('access_token');
    if (!token) {
        logout();
        return null;
    }

    const headers = { Authorization: `Bearer ${token}` };
    if (body !== undefined) headers['Content-Type'] = 'application/json';

    try {
        const response = await fetch(url, {
            method,
            headers,
            body: body === undefined ? undefined : JSON.stringify(body)
        });
        if (response.status === 401) {
            alert('Your session has expired. Please log in again.');
            logout();
            return null;
        }
        if (!response.ok) {
            alert(`Error: ${errorMessage(await response.json())}`);
            return null;
        }
        return response;
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred. Please try again.');
        return null;
    }
}

// Form fields as a plain object: {name: value}.
function formValues(form) {
    return Object.fromEntries(new FormData(form).entries());
}

// Readable message from a FastAPI error body ({"detail": "..."} or a 422 list).
function errorMessage(errorData) {
    const detail = errorData && errorData.detail;
    if (Array.isArray(detail)) {
        return detail.map((e) => `${e.loc.slice(1).join('.')}: ${e.msg}`).join('\n');
    }
    return detail || 'Request failed';
}

function getCookie(name) {
    for (const cookie of document.cookie.split(';')) {
        const [key, ...rest] = cookie.trim().split('=');
        if (key === name) return decodeURIComponent(rest.join('='));
    }
    return null;
}

// Used by the navbar's Logout button.
function logout() {
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
    window.location.href = LOGIN_PAGE;
}
