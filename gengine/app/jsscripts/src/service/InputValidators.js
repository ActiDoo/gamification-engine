import validator from 'validator';

export function isEmpty({value}){
    if(!value || value==""){
        return 'empty';
    }
    return false;
}

export function isInvalidEmail({value}){
    let isInvalidEmail = !validator.isEmail(value);
    if(isInvalidEmail){
        return 'invalidEmail';
    }
    return false;
}

export function isInvalidPassword({value}) {

    if(value.toString().length < 8) {
        return 'invalidPassword';
    }
    return false;
}