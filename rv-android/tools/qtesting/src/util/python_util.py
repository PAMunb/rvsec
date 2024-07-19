def parse_action_string(action_string):
    if '@' in action_string:
        loc = action_string.index('@')
    else:
        loc = None
    if ':' in action_string:
        loc_type = action_string.index(':')
    else:
        loc_type = None
    if ')' in action_string:
        loc_scope = action_string.rindex(')')
    else:
        loc_scope = None
    action_id = action_string[0:loc]
    if loc_type is not None and loc_scope is not None and loc_scope < loc_type:
        action_cmd = action_string[loc + 1:loc_type]
        view_string = action_string[loc_type + 1:len(action_string)]
        print(('view_string is: ' + view_string))
        loc_view_text = view_string.index('@')
        if loc_view_text is not None:
            view_type = view_string[0:loc_view_text]
            view_text = view_string[loc_view_text + 2:len(view_string) - 2]
        else:
            view_type = view_string
            view_text = ''
    else:
        action_cmd = action_string[loc + 1:len(action_string)]
        view_type = ''
        view_text = ''
    return (
     action_id, action_cmd, view_type, view_text)
