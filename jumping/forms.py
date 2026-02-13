from django import forms
from .models import JumpingClass, Location, Instructor, ClassBooking, Equipment
from datetime import datetime, timedelta
from django.utils import timezone

class JumpingClassForm(forms.ModelForm):
    """Formulario para crear/editar clases"""
    
    # Definir los días de la semana como choices para CheckboxSelectMultiple
    DAYS_OF_WEEK = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    recurring_days = forms.MultipleChoiceField(
        choices=DAYS_OF_WEEK,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'days-checkbox'
        }),
        required=False,
        label="Días de repetición"
    )
    
    class Meta:
        model = JumpingClass
        fields = [
            'name', 'description', 'instructor', 'location', 'date',
            'start_time', 'end_time', 'duration', 'capacity', 'difficulty',
            'price', 'requires_equipment', 'equipment_available', 
            'recurring', 'recurring_days', 'recurring_until'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Jumping Cardio'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la clase...'
            }),
            'instructor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'location': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 30,
                'max': 120,
                'step': 15,
                'readonly': True  # Auto-calculado
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 50
            }),
            'difficulty': forms.Select(attrs={
                'class': 'form-select'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.01
            }),
            'requires_equipment': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'equipment_available': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'recurring': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'recurring_until': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'name': 'Nombre de la clase',
            'description': 'Descripción',
            'instructor': 'Instructor',
            'location': 'Ubicación',
            'date': 'Fecha',
            'start_time': 'Hora de inicio',
            'end_time': 'Hora de fin',
            'duration': 'Duración (minutos)',
            'capacity': 'Capacidad máxima',
            'difficulty': 'Dificultad',
            'price': 'Precio',
            'requires_equipment': 'Requiere equipo',
            'equipment_available': 'Equipos disponibles',
            'recurring': 'Clase recurrente',
            'recurring_days': 'Días de repetición',
            'recurring_until': 'Repetir hasta',
        }
        help_texts = {
            'duration': 'Se calcula automáticamente según las horas seleccionadas',
            'recurring_days': 'Selecciona los días en que se repetirá la clase',
            'recurring_until': 'Fecha límite para la repetición de la clase',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        date = cleaned_data.get('date')
        recurring = cleaned_data.get('recurring')
        recurring_days = cleaned_data.get('recurring_days')
        recurring_until = cleaned_data.get('recurring_until')
        
        # Validar horarios
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('La hora de fin debe ser posterior a la hora de inicio')
        
        # Validar fecha
        if date and date < timezone.now().date():
            raise forms.ValidationError('No se pueden programar clases en fechas pasadas')
        
        # Validar campos recurrentes
        if recurring:
            if not recurring_days:
                raise forms.ValidationError('Debes seleccionar al menos un día de repetición para clases recurrentes')
            
            if not recurring_until:
                raise forms.ValidationError('Debes especificar una fecha límite para clases recurrentes')
            
            if recurring_until and date and recurring_until < date:
                raise forms.ValidationError('La fecha límite debe ser posterior a la fecha de inicio')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Convertir los días seleccionados a lista de enteros
        if self.cleaned_data.get('recurring_days'):
            # Convertir los valores de string a int
            instance.recurring_days = [int(day) for day in self.cleaned_data['recurring_days']]
        else:
            instance.recurring_days = []
        
        if commit:
            instance.save()
        
        return instance

class ClassBookingForm(forms.ModelForm):
    """Formulario para reservas"""
    
    class Meta:
        model = ClassBooking
        fields = ['client', 'payment_status', 'amount_paid', 'notes']
        widgets = {
            'client': forms.Select(attrs={
                'class': 'form-select'
            }),
            'payment_status': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'amount_paid': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 0.01,
                'min': 0
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notas adicionales...'
            }),
        }
        labels = {
            'client': 'Cliente',
            'payment_status': 'Pagado',
            'amount_paid': 'Monto pagado',
            'notes': 'Notas',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si estamos en una clase específica, podemos establecer el precio por defecto
        if 'initial' not in kwargs:
            self.fields['amount_paid'].widget.attrs['readonly'] = False

class InstructorForm(forms.ModelForm):
    """Formulario para instructores"""
    
    class Meta:
        model = Instructor
        fields = ['first_name', 'last_name', 'phone', 'email', 
                 'specialization', 'bio', 'photo', 'active', 'hire_date']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '10 dígitos'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'specialization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Jumping Cardio, Fitness, etc.'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Biografía del instructor...'
            }),
            'photo': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://ejemplo.com/foto.jpg'
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'hire_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'phone': 'Teléfono',
            'email': 'Email',
            'specialization': 'Especialización',
            'bio': 'Biografía',
            'photo': 'URL de foto',
            'active': 'Instructor activo',
            'hire_date': 'Fecha de contratación',
        }
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Eliminar cualquier caracter que no sea número
            phone = ''.join(filter(str.isdigit, phone))
            if len(phone) != 10:
                raise forms.ValidationError('El teléfono debe tener 10 dígitos')
        return phone

class LocationForm(forms.ModelForm):
    """Formulario para ubicaciones"""
    
    class Meta:
        model = Location
        fields = ['name', 'address', 'phone', 'email', 'capacity', 
                 'is_active', 'opening_time', 'closing_time']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la sede'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Dirección completa'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '10 dígitos'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Capacidad máxima'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'opening_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'closing_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
        }
        labels = {
            'name': 'Nombre de la ubicación',
            'address': 'Dirección',
            'phone': 'Teléfono',
            'email': 'Email',
            'capacity': 'Capacidad máxima',
            'is_active': 'Ubicación activa',
            'opening_time': 'Hora de apertura',
            'closing_time': 'Hora de cierre',
        }
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            if len(phone) != 10:
                raise forms.ValidationError('El teléfono debe tener 10 dígitos')
        return phone
    
    def clean(self):
        cleaned_data = super().clean()
        opening_time = cleaned_data.get('opening_time')
        closing_time = cleaned_data.get('closing_time')
        
        if opening_time and closing_time and opening_time >= closing_time:
            raise forms.ValidationError('La hora de cierre debe ser posterior a la hora de apertura')
        
        return cleaned_data