// Multi-select handler
$("#subject-select").multiselect({
  includeSelectAllOption: true,
  numberDisplayed: 1,
  onChange: function (option, checked, select) {
    var csub = $(option).val();
    if (checked) {
      if (!subs.includes(csub)) subs.push(csub);
    } else {
      var idx = subs.indexOf(csub);
      if (idx >= 0) subs.splice(idx, 1);
    }
    update_filtering({ subs: subs, all_subs: all_subs });
  },  
  onSelectAll: function (options) {
    subs = all_subs;
    update_filtering({ subs: subs, all_subs: all_subs });
  },
  onDeselectAll: function (options) {
    subs = [];
    update_filtering({ subs: subs, all_subs: all_subs });
  },
  
  buttonTitle: function (options, select) {
    return "";
  },
});
