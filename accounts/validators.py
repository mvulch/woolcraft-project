from django.contrib.auth.password_validation import MinimumLengthValidator


class BgMinimumLengthValidator(MinimumLengthValidator):

    def get_error_message(self):
        if self.min_length == 1:
            return "Паролата е прекалено къса. Трябва да съдържа поне 1 символ."
        return f"Паролата е прекалено къса. Трябва да съдържа поне {self.min_length} символа."

    def get_help_text(self):
        if self.min_length == 1:
            return "Паролата трябва да съдържа поне 1 символ."
        return f"Паролата трябва да съдържа поне {self.min_length} символа."
