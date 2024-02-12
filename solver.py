from ortools.sat.python import cp_model
import math


def get_schedule(num_classrooms, weekdays_info, classes_info, teachers_info):
    model = cp_model.CpModel()
    interval_vars = {}
    classes = []
    for i, classroom in enumerate(classes_info):
        for _ in range(classroom["amount"]):
            classes.append({
                "subject": classroom["subject"],
                "duration_in_30_minutes_periods": math.ceil((classroom["duration_hours"] * 60 + classroom["duration_minutes"]) / 30),
                "classroom": model.NewIntVar(0, num_classrooms - 1, f"class_{i}"),
                "weekday": model.NewIntVar(0, len(weekdays_info) - 1, f"weekday_{i}"),
                "start_period": model.NewIntVar(0, 47, f"start_period_{i}"),
                "teacher": model.NewIntVar(0, len(teachers_info) - 1, f"teacher_{i}"),
            })
    for cl in classes:
        for i, teacher in enumerate(teachers_info):
            if cl["subject"] not in teacher["subjects"]:
                model.Add(cl["teacher"] != i)
        for i, weekday_info in enumerate(weekdays_info):
            if not weekday_info["open"]:
                model.Add(cl["weekday"] != i)
            else:
                start_period, end_period = weekday_info["start"].hour*2 + weekday_info["start"].minute//30, weekday_info["end"].hour*2 + weekday_info["end"].minute//30
                model.Add(cl["start_period"] + cl["duration_in_30_minutes_periods"] <= end_period)
                model.Add(cl["start_period"] >= start_period)
    for i in range(len(classes) - 1):
        for j in range(i + 1, len(classes)):
            same_weekday = model.NewBoolVar(f"same_weekday_{i}_{j}")
            model.Add(classes[i]["weekday"] == classes[j]["weekday"]).OnlyEnforceIf(same_weekday)
            model.Add(classes[i]["weekday"] != classes[j]["weekday"]).OnlyEnforceIf(same_weekday.Not())
            same_classroom = model.NewBoolVar(f"same_classroom_{i}_{j}")
            model.Add(classes[i]["classroom"] == classes[j]["classroom"]).OnlyEnforceIf(same_classroom)
            model.Add(classes[i]["classroom"] != classes[j]["classroom"]).OnlyEnforceIf(same_classroom.Not())
            same_teacher = model.NewBoolVar(f"same_teacher_{i}_{j}")
            model.Add(classes[i]["teacher"] == classes[j]["teacher"]).OnlyEnforceIf(same_teacher)
            model.Add(classes[i]["teacher"] != classes[j]["teacher"]).OnlyEnforceIf(same_teacher.Not())
            classroom_overlap = model.NewBoolVar(f"classroom_overlap_{i}_{j}")
            model.AddBoolAnd([same_weekday, same_classroom]).OnlyEnforceIf(classroom_overlap)
            model.AddBoolOr([same_weekday.Not(), same_classroom.Not()]).OnlyEnforceIf(classroom_overlap.Not())
            teacher_overlap = model.NewBoolVar(f"teacher_overlap_{i}_{j}")
            model.AddBoolAnd([same_weekday, same_teacher]).OnlyEnforceIf(teacher_overlap)
            model.AddBoolOr([same_weekday.Not(), same_teacher.Not()]).OnlyEnforceIf(teacher_overlap.Not())
            must_not_overlap = model.NewBoolVar(f"must_not_overlap_{i}_{j}")
            model.AddBoolOr([classroom_overlap, teacher_overlap]).OnlyEnforceIf(must_not_overlap)
            model.AddBoolAnd([classroom_overlap.Not(), teacher_overlap.Not()]).OnlyEnforceIf(must_not_overlap.Not())
            
            interval_vars[(i, j)] = model.NewOptionalFixedSizeIntervalVar(
                classes[i]["start_period"],
                classes[i]["duration_in_30_minutes_periods"],
                must_not_overlap,
                f"interval_{i}_{j}"
            )
            interval_vars[(j, i)] = model.NewOptionalFixedSizeIntervalVar(
                classes[j]["start_period"],
                classes[j]["duration_in_30_minutes_periods"],
                must_not_overlap,
                f"interval_{j}_{i}"
            )
            model.AddNoOverlap([interval_vars[(i, j)], interval_vars[(j, i)]])
            
            

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60
    status = solver.Solve(model)
    print(solver.StatusName(status))
    if status == cp_model.OPTIMAL:
        schedule = []
        for cl in classes:
            #print(solver.Value(cl["interval_var"].StartExpr()), solver.Value(cl["interval_var"].EndExpr()))
            schedule.append({
                "subject": cl["subject"],
                "duration": cl["duration_in_30_minutes_periods"]*30,
                "classroom": solver.Value(cl["classroom"]),
                "weekday": solver.Value(cl["weekday"]),
                "start_period": solver.Value(cl["start_period"]),
                "end_period": solver.Value(cl["start_period"]) + cl["duration_in_30_minutes_periods"],
                "teacher": teachers_info[solver.Value(cl["teacher"])]["name"],
            })
        return schedule
    else:
        return None
    