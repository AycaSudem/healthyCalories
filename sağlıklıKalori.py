import tkinter as tk
from tkinter import messagebox, ttk
import pandas as pd
import random
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from tkinter.filedialog import asksaveasfilename


nutrition_df = pd.read_excel("nutrition.xlsx", skiprows=2, header=None)
nutrition_df = nutrition_df[[1, 4, 5, 3, 2]]
nutrition_df.columns = ['Food', 'Protein', 'Fat', 'Carbohydrate', 'Calories']

for col in ['Protein', 'Carbohydrate', 'Fat', 'Calories']:
    nutrition_df[col] = nutrition_df[col].astype(str).str.replace("g", "").str.replace(",", ".").str.strip()
    nutrition_df[col] = pd.to_numeric(nutrition_df[col], errors='coerce')

blocked_foods = ["infant formula", "alcohol", "candy", "energy drink", "liqueur", "vodka", "rum", "whiskey", "syrup"]
nutrition_df_cleaned = nutrition_df[~nutrition_df['Food'].str.lower().str.contains('|'.join(blocked_foods))].copy()
nutrition_df_cleaned.dropna(inplace=True)


root = tk.Tk()
root.title("Diet Planner")
root.geometry("650x800")

frame = tk.Frame(root)
frame.pack(pady=10)

inputs = {}
fields = [("Weight (kg):", "weight"), ("Height (cm):", "height"), ("Age:", "age")]

for label_text, key in fields:
    tk.Label(frame, text=label_text).pack()
    entry = tk.Entry(frame)
    entry.pack()
    inputs[key] = entry

tk.Label(frame, text="Gender:").pack()
gender_combo = ttk.Combobox(frame, values=["Male", "Female"], state="readonly")
gender_combo.pack()
inputs['gender'] = gender_combo

tk.Label(frame, text="Goal:").pack()
goal_combo = ttk.Combobox(frame, values=["Lose weight", "Gain weight", "Maintain"], state="readonly")
goal_combo.pack()
inputs['goal'] = goal_combo

tk.Label(frame, text="Activity Level:").pack()
activity_combo = ttk.Combobox(frame, values=["Sedentary", "Lightly active", "Moderately active", "Very active", "Extra active"], state="readonly")
activity_combo.pack()
inputs['activity'] = activity_combo

tk.Label(frame, text="Diet Type:").pack()
diet_combo = ttk.Combobox(frame, values=["None", "Vegetarian", "Vegan"], state="readonly")
diet_combo.pack()
inputs['diet'] = diet_combo

tk.Button(root, text="🍽️ Generate Diet Plan", command=lambda: generate_diet()).pack(pady=10)

output_frame = tk.Frame(root)
output_frame.pack()
output_text = tk.Text(output_frame, height=25, width=80, wrap=tk.WORD)
scrollbar = tk.Scrollbar(output_frame, command=output_text.yview)
output_text.config(yscrollcommand=scrollbar.set)
output_text.pack(side=tk.LEFT, fill=tk.BOTH)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)


def save_to_pdf():
    content = output_text.get("1.0", tk.END)
    if not content.strip():
        messagebox.showwarning("Warning", "No diet plan to save.")
        return

    filepath = asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if not filepath:
        return

    try:
        c = canvas.Canvas(filepath, pagesize=A4)
        width, height = A4
        lines = content.strip().split("\n")
        y = height - 40
        for line in lines:
            if y < 40:
                c.showPage()
                y = height - 40
            c.drawString(40, y, line)
            y -= 15
        c.save()
        messagebox.showinfo("Success", "PDF saved successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Could not save PDF:\n{str(e)}")

tk.Button(root, text="📄 Save as PDF", command=save_to_pdf).pack(pady=5)


def calculate_bmi(weight, height):
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    if bmi < 18.5:
        status = "Underweight"
    elif 18.5 <= bmi < 24.9:
        status = "Normal weight"
    elif 25 <= bmi < 29.9:
        status = "Overweight"
    else:
        status = "Obese"
    return round(bmi, 1), status

def calculate_ideal_weight(height):
    return round((height - 100 + (height - 150) / 4), 1)

def calculate_calories(weight, height, age, gender, activity, goal):
    bmr = 10 * weight + 6.25 * height - 5 * age + (5 if gender == "male" else -161)
    multiplier = {
        "sedentary": 1.2,
        "lightly active": 1.375,
        "moderately active": 1.55,
        "very active": 1.725,
        "extra active": 1.9
    }[activity]
    calories = bmr * multiplier
    if goal == "lose weight":
        calories -= 500
    elif goal == "gain weight":
        calories += 500
    return calories

def calculate_macros(calories, goal):
    if goal == "lose weight":
        p, c, f = 0.4, 0.4, 0.2
    elif goal == "gain weight":
        p, c, f = 0.3, 0.5, 0.2
    else:
        p, c, f = 0.35, 0.45, 0.2
    return round((calories * c) / 4, 2), round((calories * p) / 4, 2), round((calories * f) / 9, 2)


def generate_meal_plan(carb, protein, fat, intolerances):
    meals = {
        "Breakfast": {"Protein": 0.25, "Carbohydrate": 0.5, "Fat": 0.25},
        "Lunch": {"Protein": 0.35, "Carbohydrate": 0.3, "Fat": 0.35},
        "Dinner": {"Protein": 0.35, "Carbohydrate": 0.3, "Fat": 0.35},
        "Snack": {"Protein": 0.05, "Carbohydrate": 0.1, "Fat": 0.05}
    }

    plan = {}

    for meal, ratio in meals.items():
        p_target = protein * ratio['Protein']
        c_target = carb * ratio['Carbohydrate']
        f_target = fat * ratio['Fat']

        df = nutrition_df_cleaned.copy()

        for item in intolerances:
            df = df[~df['Food'].str.lower().str.contains(item)]

        df["total_diff"] = (
            abs(df["Protein"] - p_target) +
            abs(df["Carbohydrate"] - c_target) +
            abs(df["Fat"] - f_target)
        )

        top_matches = df.sort_values("total_diff").head(10).sample(3, random_state=random.randint(0, 9999))

        items = []
        for _, row in top_matches.iterrows():
            items.append(f"{row['Food']} - P: {row['Protein']}g, C: {row['Carbohydrate']}g, F: {row['Fat']}g")

        plan[meal] = items

    return plan


def generate_diet():
    try:
        weight = float(inputs['weight'].get())
        height = float(inputs['height'].get())
        age = int(inputs['age'].get())
        gender = inputs['gender'].get().lower()
        goal = inputs['goal'].get().lower()
        activity = inputs['activity'].get().lower()
        diet = inputs['diet'].get().lower()

        bmi, status = calculate_bmi(weight, height)
        ideal = calculate_ideal_weight(height)

        adjusted_goal = goal
        alert = ""

        if goal == "lose weight" and weight <= ideal:
            adjusted_goal = "maintain"
            alert = "Your weight is at or below ideal. Switching goal to 'maintain weight'."
        elif goal == "gain weight" and weight >= ideal:
            adjusted_goal = "lose weight"
            alert = "Your weight is above ideal. Switching goal to 'lose weight'."

        intolerances = []
        if diet == "vegan":
            intolerances = ["meat", "egg", "milk", "cheese", "yogurt"]
        elif diet == "vegetarian":
            intolerances = ["meat"]

        cal = calculate_calories(weight, height, age, gender, activity, adjusted_goal)
        carbs, protein, fat = calculate_macros(cal, adjusted_goal)
        meal_plan = generate_meal_plan(carbs, protein, fat, intolerances)

        output_text.delete("1.0", tk.END)
        if alert:
            output_text.insert(tk.END, f"⚠️ {alert}\n\n")
        output_text.insert(tk.END, f"BMI: {bmi} ({status})\nIdeal Weight: {ideal} kg\nSuggested Goal: {adjusted_goal}\n")
        output_text.insert(tk.END, f"Daily Calories: {cal:.0f}\nCarbs: {carbs}g, Protein: {protein}g, Fat: {fat}g\n\n")

        for meal, items in meal_plan.items():
            output_text.insert(tk.END, f"{meal}:\n")
            for i in items:
                output_text.insert(tk.END, f" - {i}\n")
            output_text.insert(tk.END, "\n")

    except Exception as e:
        messagebox.showerror("Error", str(e))

root.mainloop()
