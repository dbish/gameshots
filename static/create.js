function readURL(input) {
  if (input.files && input.files[0]) {
    var reader = new FileReader();
    
    reader.onload = function(e) {
      $('#imgPreview').attr('src', e.target.result);
    }
    
    reader.readAsDataURL(input.files[0]); // convert to base64 string
    $('#imgPreview').show();
  }
  else {
	  $('#imgPreview').hide();
  }
}

window.onload = function(){
	$("#imgInput").change(function() {
	  readURL(this);
	});

	$('#game').autocomplete({
		source: function (request, response){
			$.ajax({
				url: "/autocompleteGames",
				dataType: "json",
				data: {
					term: request.term
				},
				success: function(data){
					response(data);
				}
			});
		},
		minLength: 2,
		select: function(event, ui){
			console.log('selected:'+ui.item.value);
		}
	});
};
