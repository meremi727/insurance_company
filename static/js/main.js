function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

async function show_permission_denied_toast_when_no_perms(element) {
    const url = element.getAttribute("url");
    result = false
    await fetch(url, {
        method: 'HEAD'
    }).then(headResponse => {
        if (headResponse.status !== 403) {
            result = true
            window.location.href = url;
        } else {
            toast = new bootstrap.Toast(document.getElementById("permision-denied-toast"))
            toast.show()
        }
    });

    return result
}

function show_success(message) {
    elem = document.getElementById("success-toast")
    if (message !== null && message !== '')
        elem.querySelector('.toast-body').innerHTML = message
    toast = new bootstrap.Toast(elem)
    toast.show()
}

function show_error(message) {
    elem = document.getElementById("error-toast")
    if (message !== null && message !== '')
        elem.querySelector('.toast-body').innerHTML = message
    toast = new bootstrap.Toast(elem)
    toast.show()
}
