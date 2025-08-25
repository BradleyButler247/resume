from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, widgets, SelectMultipleField
from wtforms.validators import InputRequired, Optional, Email, Length
from markupsafe import Markup

class RegisterForm(FlaskForm):
    first_name = StringField("First Name", validators=[InputRequired()])
    last_name = StringField("Last Name", validators=[InputRequired()])
    email = StringField("Email", validators=[InputRequired(), Email()])
    profile_pic = StringField('Image URL (Optional)', validators=[Optional()])
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[Length(min=6)])


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])

class EditProfileForm(FlaskForm):
    first_name = StringField("First Name", validators=[Optional()])
    last_name = StringField("Last Name", validators=[Optional()])
    email = StringField("Email", validators=[Optional(), Email()])
    profile_pic = StringField('Image URL (Optional)', validators=[Optional()])
    username = StringField("Username", validators=[Optional()])
    password = PasswordField("Password", validators=[Length(min=6)])


class BootstrapListWidget(widgets.ListWidget):
 
    def __call__(self, field, **kwargs):
        kwargs.setdefault("id", field.id)
        html = [f"<{self.html_tag} {widgets.html_params(**kwargs)}>"]
        for subfield in field:
            if self.prefix_label:
                html.append(f"<li class='list-group-item'>{subfield.label} {subfield(class_='form-check-input ms-1')}</li>")
            else:
                html.append(f"<li class='list-group-item'>{subfield(class_='form-check-input me-1')} {subfield.label}</li>")
        html.append("</%s>" % self.html_tag)
        return Markup("".join(html))
 

class MultiCheckboxField(SelectMultipleField):
    widget = BootstrapListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class FilterRecipesForm(FlaskForm):
    filters = MultiCheckboxField('Filters', choices=[('vegetarian', 'Vegetarian'),
                                                     ('vegan', 'Vegan'),
                                                     ('glutenFree', 'Gluten Free'),
                                                     ('dairyFree', 'Dairy Free'),
                                                     ('veryHealthy', 'Very Healthy'),
                                                     ('cheap', 'Cheap'),
                                                     ('veryPopular', 'Very Popular'),
                                                     ('sustainable', 'Sustainable')])


class IngredientSubsForm(FlaskForm):
    ingredient = StringField("Ingredient", validators=[InputRequired()])


class ShopIngredientsForm(FlaskForm):
    ingredient = StringField("Ingredient", validators=[InputRequired()])