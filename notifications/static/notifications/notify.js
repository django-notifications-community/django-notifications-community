var notify_badge_class;
var notify_menu_class;
var notify_api_url;
var notify_fetch_count;
var notify_unread_url;
var notify_mark_all_unread_url;
var notify_refresh_period = 15000;
// Set notify_mark_as_read to true to mark notifications as read when fetched
var notify_mark_as_read = false;

let consecutive_misfires = 0;
const registered_functions = [];

function fill_notification_badge(data) {
    for (const badge of document.getElementsByClassName(notify_badge_class)) {
        badge.textContent = data.unread_count;
    }
}

function fill_notification_list(data) {
    const fragment = document.createDocumentFragment();

    for (const item of data.unread_list) {
        let message = '';
        if (item.actor) {
            message = item.actor;
        }
        if (item.verb) {
            message += ` ${item.verb}`;
        }
        if (item.target) {
            message += ` ${item.target}`;
        }
        if (item.timestamp) {
            message += ` ${item.timestamp}`;
        }
        const li = document.createElement('li');
        li.textContent = message;
        fragment.appendChild(li);
    }

    for (const menu of document.getElementsByClassName(notify_menu_class)) {
        menu.innerHTML = '';
        menu.appendChild(fragment.cloneNode(true));
    }
}

function register_notifier(func) {
    registered_functions.push(func);
}

async function fetch_api_data() {
    if (registered_functions.length > 0) {
        let params = `?max=${notify_fetch_count}`;
        if (notify_mark_as_read) {
            params += '&mark_as_read=true';
        }

        try {
            const response = await fetch(notify_api_url + params);
            if (response.ok) {
                consecutive_misfires = 0;
                const data = await response.json();
                for (const func of registered_functions) {
                    func(data);
                }
            } else {
                consecutive_misfires++;
            }
        } catch (e) {
            consecutive_misfires++;
        }
    }

    if (consecutive_misfires < 10) {
        setTimeout(fetch_api_data, notify_refresh_period);
    } else {
        for (const badge of document.getElementsByClassName(notify_badge_class)) {
            badge.textContent = '!';
            badge.title = 'Connection lost!';
        }
    }
}

function _resolveCallback(name) {
    const parts = name.split('.');
    let obj = window;
    for (const part of parts) {
        obj = obj[part];
        if (typeof obj === 'undefined') {
            return undefined;
        }
    }
    return obj;
}

function _initNotifyConfig() {
    const el = document.getElementById('notify-config');
    if (!el) {
        return;
    }
    let config;
    try {
        config = JSON.parse(el.textContent);
    } catch (e) {
        return;
    }

    notify_badge_class = config.badgeClass;
    notify_menu_class = config.menuClass;
    notify_api_url = config.apiUrl;
    notify_fetch_count = config.fetchCount;
    notify_unread_url = config.unreadUrl;
    notify_mark_all_unread_url = config.markAllUnreadUrl;
    notify_refresh_period = config.refreshPeriod;
    notify_mark_as_read = config.markAsRead;

    if (config.callbacks) {
        for (const name of config.callbacks) {
            const fn = _resolveCallback(name);
            if (typeof fn === 'function') {
                register_notifier(fn);
            }
        }
    }

    setTimeout(fetch_api_data, 1000);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _initNotifyConfig);
} else {
    _initNotifyConfig();
}
