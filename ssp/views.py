# Create your views here.
from django.shortcuts import *
from django.views import generic
from django.forms import modelformset_factory, modelform_factory, Textarea
import django_filters
import logging
from django.http import HttpResponseRedirect
import urllib
import os
from ssp.models.base_classes_and_fields import *
from ssp.models.controls import *
from django.contrib import messages

from .models import system_control, system_security_plan, nist_control, control_parameter, control_statement
from .forms import SystemSecurityPlan, ImportCatalogForm, import_catalog

from django.core.files import File
from scripts.OSCAL_Catalog_import import run


def ssp_new(request):
    if request.method == "POST":
        form = SystemSecurityPlan(request.POST)
        if form.is_valid():
            ssp = form.save()
            return redirect('system_security_plan_detail_view', pk=ssp.pk)
    else:
        form = SystemSecurityPlan()
    return render(request, 'ssp/ssp_edit.html', {'form': form})


def ssp_edit(request, pk):
    ssp = get_object_or_404(system_security_plan, pk=pk)
    if request.method == "POST":
        form = SystemSecurityPlan(request.POST, instance=ssp)
        if form.is_valid():
            form.save()
            return redirect('system_security_plan_detail_view', pk=pk)
    else:
        form = SystemSecurityPlan(instance=ssp)
    return render(request, 'ssp/ssp_edit.html', {'form': form})


def system_control_edit(request, pk):
    sc = get_object_or_404(system_control, pk=pk)
    sc_FormSet = modelformset_factory(system_control,fields=('control_status','control_origination'))
    sc_paramFormSet = modelformset_factory(control_parameter, fields=('control_parameter_id','value'), widgets={'value': Textarea(attrs={'cols':30,'rows':1})})
    sc_statementFormSet = modelformset_factory(control_statement, fields=('control_statement_id','control_statement_text'))
    if request.method == "POST":
        sc_paramFormSet = sc_paramFormSet(queryset=control_parameter.objects.filter(system_control=sc.id))
        if sc_paramFormSet.is_valid():
            sc_paramFormSet.save(commit=False)
            # paramater Titles are control title - paramater id
            sc_paramFormSet.title = sc.title + ' - ' + sc_paramFormSet.control_parameter_id
            # paramater short_name should be the control it relates to
            sc_paramFormSet.short_name = sc.short_name
            sc_paramFormSet.save()
        else:
            form_is_not_valid = True
        if sc_statementFormSet.is_valid():
            sc_statementFormSet.save(commit=False)
            # Statement Titles are control title - paramater id
            sc_statementFormSet.title = sc.title + ' - ' + sc_statementFormSet.control_statement_id
            # Statement short_name should be the control it relates to
            sc_statementFormSet.short_name = sc.short_name
            sc_statementFormSet.save()
        else:
            form_is_not_valid = True
        if sc_FormSet.is_valid():
            sc_FormSet.save()
        else:
            form_is_not_valid = True
        if not form_is_not_valid:
            return redirect('ssp/system_control_edit.html', pk=pk)
    else:
        sc_formset = sc_FormSet(queryset=system_control.objects.filter(pk=sc.id))
        param_formset = sc_paramFormSet(queryset=control_parameter.objects.filter(system_control=sc.id))
        statement_formset = sc_statementFormSet(queryset=control_statement.objects.filter(system_control=sc.id))
    return render(request, 'ssp/system_control_edit.html', {'object': sc,'sc_formset': sc_formset,'param_formset':param_formset,'statement_formset':statement_formset})

class nist_control_list_view(generic.ListView):
    model = nist_control
    queryset = nist_control.objects.order_by('sort_id')


class nist_control_detail_view(generic.DetailView):
    model = nist_control


class system_control_list_view_filter(django_filters.FilterSet):
    class Meta:
        model = system_control
        fields = ['control_status','nist_control__group_title','control_primary_system']

class system_control_list_view(generic.ListView):
    model = system_control


class system_control_detail_view(generic.DetailView):
    model = system_control


class system_security_plan_list_view(generic.ListView):
    model = system_security_plan
    queryset = system_security_plan.objects.order_by('title')


class system_security_plan_detail_view(generic.DetailView):
    model = system_security_plan
    log = logging.getLogger(__name__)
    log.info('ssp ',object.__name__,'viewed by')


# Imaginary function to handle an uploaded file.
#from somewhere import handle_uploaded_file

def import_catalog(request):
    if request.method == 'POST':
        form = ImportCatalogForm(request.POST, request.FILES)

        if form.is_valid():
            catalog = form.save(commit=False)
            if len(request.FILES) != 0:
                catalog.file = request.FILES['file']
            if form.cleaned_data['file_url']:
                result = urllib.request.urlretrieve(form.cleaned_data['file_url'])
                catalog.file.save(os.path.basename(form.cleaned_data['file_url']), File(open(result[0], 'rb')))
            catalog.save()
            if request.user.is_authenticated:
                catalog.user = request.user.username
                catalog.save()

            try:
                catalog_control_baseline = control_baseline.objects.get(title=catalog.title)
            except control_baseline.DoesNotExist:
                catalog_control_baseline = control_baseline(title=catalog.title)
                catalog_control_baseline.save()

            catalog.control_baseline = catalog_control_baseline
            catalog.save()

            if catalog.file_url:
                try:
                    catalog_link = link.objects.get(href=catalog.file_url)
                except link.DoesNotExist:
                    catalog_link = link(text=catalog.title, href=catalog.file_url)
                    catalog_link.save()

                catalog_control_baseline.link = catalog_link
                catalog_control_baseline.save()

            # form.save()

            if form.cleaned_data['file']:
                file_path =str(catalog.file)
                catalog_name = str(form.cleaned_data['file'])
            else:
                file_path = form.cleaned_data['file_url']
                file_path_list = file_path.split('/')
                catalog_name = file_path_list[-1]

            added, updated = run(str(catalog.file), catalog_name)
            catalog.added_controls = added
            catalog.updated_controls = updated
            catalog.save()

            messages.success(request, 'Imported OSCAL Catalog successfully. Added '+str(added)+ ' and updated '+ str(updated)+ ' NIST Controls.')
            return render(request, 'ssp\import_catalog.html', {'form': form})
            #return HttpResponse("data submitted successfully")

        else:
            return render(request, 'ssp\import_catalog.html', {'form': form})
    else:
        form = ImportCatalogForm()
        return render(request, 'ssp\import_catalog.html', {'form': form})
