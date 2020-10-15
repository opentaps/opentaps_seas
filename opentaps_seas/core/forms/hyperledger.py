from django import forms


class HyperLedgerQueryAdminForm(forms.Form):
    name = forms.CharField()

    class Meta:
        fields = ["name"]


class HyperLedgerEnrollUserForm(forms.Form):
    affiliation = forms.CharField()

    class Meta:
        fields = ["affiliation"]

