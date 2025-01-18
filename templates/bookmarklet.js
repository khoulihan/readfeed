javascript: (function() {xhr = new XMLHttpRequest(); let u = document.location.href; xhr.open("GET", encodeURI("{{ url_for('add') }}?url=" + u)); xhr.send();}());
