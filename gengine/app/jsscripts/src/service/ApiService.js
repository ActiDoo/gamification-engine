import config from '../config';

export function getApiUrl(url) {
    return `${config.apiUrl}/${url ? url : ''}`;
};
