from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("",views.index,name="index"),   
    path("voters/",views.voters_info,name="voters_info"),# voter list   
    path("voters/<int:voter_list_id>/", views.single_voters_info,name="single_voters_info"),# single voter info
    path("voter_add/",views.add_voter,name="add_voter"),# voter addition    
    path("voter_update/<int:voter_list_id>/", views.update_voter, name="update_voter"),# voter update   
    path("tags/",views.tags,name="tags"),# tags   
    path("voters/search/", views.voters_search, name="voters_search"),# voter search api    
    path("voters/family_search/",views.family_dropdown_search, name = "family_dropdown_search"),# voter family search  
    path("roles/",views.roles,name="roles"),# roles 
    path("voters/relation_add/",views.add_relation,name="add_relation"),# voter relation add 
    path("voters/relation_remove/",views.remove_relation,name="remove_relation"),# voter relation remove
    path("voters/filter/",views.filter,name="filter"),# filter 
    path("dropdown/religion/",views.religion_dropdown,name="religion_dropdown"),
    path("dropdown/caste/",views.caste_dropdown,name="caste_dropdown"),
    path("dropdown/occupation/",views.occupation_dropdown,name="occupation_dropdown"),
    path('registration/',views.registration,name="registration"),
    path("registration/login/",views.id_validation,name="id_validation"),
    path("registration/change_password/",views.password_change,name="password_change"),
    
    path("admin/dashboard/",views.dashboard,name="dashboard"),# dashboard 
    
    path("admin/dashboard/allocated/",views.admin_allocation_panel,name="allocated_screen"),
    path("admin/dashboard/unassigned_list/",views.unassigned_voters,name="unassigned_voters"),
    
    path("admin/dashboard/assign/",views.assign_voters_to_karyakarta,name="assign_voters_to_karyakarta"),
    path("admin/dashboard/auto_assign/",views.auto_select_unassigned_voters,name="auto_select_unassigned_voters"),
    path("admin/dashboard/list_volunteer/",views.list_volunteers,name="list_volunteers"),
    
    path("admin/dashboard/volunteers/<int:user_id>/",views.single_volunteer,name="single_volunteer"),
    path("admin/dashboard/assign_role/",views.promote_user,name="promote_user"),
    
    path("admin/dashboard/comments/",views.all_comments,name="all_comments"),
    path("subadmin/dashboard/",views.admin_dashboard,name="admin_dashboard"),
    path("subadmin/dashboard/allocated/",views.volunteer_allocation_panel,name="volunteer_allocation_panel"),
    
    path("volunteer/dashboard/",views.volunteer_dashboard,name="volunteer_dashboard"),
    path("volunteer/dashboard/list_voters/",views.volunteer_voters_page,name="volunteer_voters_page"),
    path("volunteer/dashboard/list_voters/filter/",views.volunteer_voters_page_filter,name="volunteer_voters_page_filter"),
    
    path("volunteer/dashboard/delete/<int:user_id>/",views.delete_user,name="delete_user"),
    
    path("permissions/all/",views.get_all_roles_permissions,name="get_all_roles_permissions"),
    path("permissions/role/",views.get_roles_permissions,name="get_roles_permissions"),
    
    path("permissions/all/update/",views.bulk_update_permissions,name="bulk_update_permissions"),
    path("voters/export-excel/",views.export_voters_excel,name="export_voters_excel"),
    
    path("regirstration/upload_excel/",views.upload_login_credentials_excel,name="upload_login_credentials_excel"),
    path("regirstration/upload_excel/list/",views.list_uploaded_login_excels,name="list_uploaded_login_excels"),
    path("regirstration/upload_excel/list/download/<int:excel_id>/",views.download_login_excel,name="download_login_excel"),
    
    path("mobile_permission/",views.match_contacts_with_users,name="match_contacts_with_users"),   
    path("mobile/print/",views.print_voters_by_ids,name="print_voters_by_ids"),
]
