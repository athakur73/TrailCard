from trailapp.models import File
from rest_framework import serializers


class FileSerializer(serializers.ModelSerializer):

    class Meta:
        model = File

        fields = ('file', 'uploaded_by', 'file_status',
                  'last_modified_by', 'uploaded_date', 'last_modified_date')

        fields = '__all__'
