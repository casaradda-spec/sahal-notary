from django.contrib import admin

from .models import AuditLog, ClientProfile, Document, DocumentTemplate, NotaryProfile, Witness


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'city', 'national_id')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


@admin.register(NotaryProfile)
class NotaryProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number', 'region', 'rating')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'license_number')


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'party_type', 'requires_witnesses', 'times_used')
    list_filter = ('category', 'party_type', 'requires_witnesses')


class WitnessInline(admin.TabularInline):
    model = Witness
    extra = 0


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('ref', 'template', 'client', 'notary', 'status', 'created_at')
    list_filter = ('status', 'template')
    search_fields = ('ref', 'client__user__first_name', 'client__user__last_name')
    inlines = [WitnessInline]
    readonly_fields = ('ref', 'rendered_body', 'content_hash', 'pdf_hash', 'qr_token')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'document', 'user', 'created_at')
    list_filter = ('action',)
    search_fields = ('document__ref', 'user__username')
    readonly_fields = ('user', 'action', 'document', 'details', 'created_at')
