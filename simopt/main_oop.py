import tkinter as tk
from tkinter import ttk, Scrollbar

from directory import problem_directory
from directory import solver_directory
from directory import oracle_directory
from wrapper_base import Experiment

class Experiment_Window:
    def __init__(self, master):
        self.master = master

        self.frame = tk.Frame(self.master)

        self.experiment_master_list = []
        self.widget_list = []
        self.experiment_object_list = []
        
        self.instruction_label = tk.Label(master=self.master, # window label is used in
                            text = "Welcome to SimOpt \n Please complete the fields below to run your experiment: \n Please note: '*' are required fields",
                            font = "Calibri 15 bold")
        
        self.problem_label = tk.Label(master=self.master, # window label is used in
                        text = "Please select the type of Problem:*",
                        font = "Calibri 11 bold")
        
        # from experiments.inputs.all_factors.py:
        self.problem_list = problem_directory
        # stays the same, has to change into a special type of variable via tkinter function
        self.problem_var = tk.StringVar(master=self.master)
        # sets the default OptionMenu value
        # self.problem_var.set("----")
        # creates drop down menu, for tkinter, it is called "OptionMenu"
        self.problem_menu = ttk.OptionMenu(self.master, self.problem_var, "Problem", *self.problem_list, command=self.show_problem_factors)

        self.solver_label = tk.Label(master=self.master, # window label is used in
                        text = "Please select the type of Solver:*",
                        font = "Calibri 11 bold")

        # from experiments.inputs.all_factors.py:
        self.solver_list = solver_directory
        # stays the same, has to change into a special type of variable via tkinter function
        self.solver_var = tk.StringVar(master=self.master)
        # sets the default OptionMenu value
        # self.solver_var.set("----")
        # creates drop down menu, for tkinter, it is called "OptionMenu"
        self.solver_menu = ttk.OptionMenu(self.master, self.solver_var, "Solver", *self.solver_list, command=self.show_solver_factors)       

        self.macro_label = ttk.Label(master=self.master,
                        text = "Number of Macro Replications:*",
                        font = "Calibri 11 bold")

        self.macro_var = tk.StringVar(self.master)
        self.macro_entry = ttk.Entry(master=self.master, textvariable = self.macro_var, justify = tk.LEFT)
        self.macro_entry.insert(index=tk.END, string="10")
        
        self.run_button = ttk.Button(master=self.master, # window button is used in
                        # aesthetic of button and specific formatting options
                        text = "Run", 
                        width = 15, # width of button
                        command = self.run_single_function) # if command=function(), it will only work once, so cannot call function, only specify which one, activated by left mouse click)

        self.add_button = ttk.Button(master=self.master,
                                    text = "Add Experiment",
                                    width = 15,
                                    command=self.add_function)

        self.clear_queue_button = ttk.Button(master=self.master,
                                    text = "Clear All Experiments",
                                    width = 20,
                                    command = self.clear_queue)#(self.experiment_added, self.problem_added, self.solver_added, self.macros_added, self.run_button_added))

        self.crossdesign_button = ttk.Button(master=self.master,
                                            text = "Cross-Design Experiment",
                                            width = 25,
                                            command = self.crossdesign_function)

        self.queue_label_frame = ttk.Labelframe(master=self.master, text="Experiment")

        self.queue_canvas = tk.Canvas(master=self.queue_label_frame, borderwidth=0)

        self.queue_frame = ttk.Frame(master=self.queue_canvas)
        self.vert_scroll_bar = Scrollbar(self.queue_label_frame, orient="vertical", command=self.queue_canvas.yview)
        self.queue_canvas.configure(yscrollcommand=self.vert_scroll_bar.set)

        self.horiz_scroll_bar = Scrollbar(self.queue_label_frame, orient="horizontal", command=self.queue_canvas.xview)
        self.queue_canvas.configure(xscrollcommand=self.horiz_scroll_bar.set)

        self.vert_scroll_bar.pack(side="right", fill="y")
        self.horiz_scroll_bar.pack(side="bottom", fill="x")

        self.queue_canvas.pack(side="left", fill="both", expand=True)
        self.queue_canvas.create_window((0,0), window=self.queue_frame, anchor="nw",
                                  tags="self.queue_frame")
        
        self.queue_frame.bind("<Configure>", self.onFrameConfigure_queue)

        self.notebook = ttk.Notebook(master=self.queue_frame)
        self.notebook.pack(fill="both")

        self.tab_one = tk.Frame(master=self.notebook)

        self.notebook.add(self.tab_one, text="Queue of Experiments")

        self.tab_one.grid_rowconfigure(0)

        self.heading_list = ["Problem", "Solver", "Macro Reps", "", "Actions", ""]

        for heading in self.heading_list:
            self.tab_one.grid_columnconfigure(self.heading_list.index(heading))
            label = tk.Label(master=self.tab_one, text=heading, font="Calibri 14 bold")
            label.grid(row=0, column=self.heading_list.index(heading), padx=5, pady=3)

        self.instruction_label.place(x=0, y=0)
        #self.instruction_label.grid(row=0, column=1)

        self.problem_label.place(x=0, y=85)
        #self.problem_label.grid(row=1, column=0, pady=25)
        self.problem_menu.place(x=225, y=85)
        #self.problem_menu.grid(row=1, column=0, sticky='s')

        self.solver_label.place(x=0, y=165)
        #self.solver_label.grid(row=2, column=0, pady=25)
        self.solver_menu.place(x=225, y=165)
        #self.solver_menu.grid(row=2, column=0, sticky='s')

        self.macro_label.place(x=0, y=245)
        #self.macro_label.grid(row=3, column=0, pady=25)
        self.macro_entry.place(x=225, y=245)
        #self.macro_entry.grid(row=3, column=0, sticky='s')

        self.run_button.place(x=5, y=285)
        self.add_button.place(x=5, y=325)
        self.crossdesign_button.place(x=115, y=285)
        #self.add_button.grid(row=4, column=0, pady=25)

        #self.run_button.grid(row=4, column=0, sticky='s')

        self.clear_queue_button.place(x=115, y=325)

        # self.pathname_label.grid(row=3, column=1, sticky='n')
        # self.pathname_entry.grid(row=3, column=1, sticky='s')
        # self.pathname_button.grid(row=3, column=1)

        self.queue_label_frame.place(x=0, y=375, height=400, width=650)

        self.frame.pack(fill='both')

    def show_problem_factors(self, *args):
        print("Got the problem: ", self.problem_var.get())

        self.problem_factors_list = []

        self.factor_label_frame_problem = ttk.Labelframe(master=self.master, text="Problem Factors")

        self.factor_canvas_problem = tk.Canvas(master=self.factor_label_frame_problem, borderwidth=0)

        self.factor_frame_problem = ttk.Frame(master=self.factor_canvas_problem)
        self.vert_scroll_bar_factor_problem = Scrollbar(self.factor_label_frame_problem, orient="vertical", command=self.factor_canvas_problem.yview)
        self.factor_canvas_problem.configure(yscrollcommand=self.vert_scroll_bar_factor_problem.set)

        self.horiz_scroll_bar_factor_problem = Scrollbar(self.factor_label_frame_problem, orient="horizontal", command=self.factor_canvas_problem.xview)
        self.factor_canvas_problem.configure(xscrollcommand=self.horiz_scroll_bar_factor_problem.set)

        self.vert_scroll_bar_factor_problem.pack(side="right", fill="y")
        self.horiz_scroll_bar_factor_problem.pack(side="bottom", fill="x")

        self.factor_canvas_problem.pack(side="left", fill="both", expand=True)
        self.factor_canvas_problem.create_window((0,0), window=self.factor_frame_problem, anchor="nw",
                                  tags="self.factor_frame_problem")
        
        self.factor_frame_problem.bind("<Configure>", self.onFrameConfigure_factor_problem)

        self.factor_notebook_problem = ttk.Notebook(master=self.factor_frame_problem)
        self.factor_notebook_problem.pack(fill="both")

        self.factor_tab_one_problem = tk.Frame(master=self.factor_notebook_problem)

        self.factor_notebook_problem.add(self.factor_tab_one_problem, text=str(self.problem_var.get()) + " Factors")

        self.factor_tab_one_problem.grid_rowconfigure(0)

        self.factor_heading_list_problem = ["Description", "Input"]

        for heading in self.factor_heading_list_problem:
            self.factor_tab_one_problem.grid_columnconfigure(self.factor_heading_list_problem.index(heading))
            label_problem = tk.Label(master=self.factor_tab_one_problem, text=heading, font="Calibri 14 bold")
            label_problem.grid(row=0, column=self.factor_heading_list_problem.index(heading), padx=5, pady=3)

        self.problem_factor_confirm_button = ttk.Button(master=self.master, # window button is used in
                    # aesthetic of button and specific formatting options
                    text = "Confirm Problem Factors",
                    command = self.test_function)

        self.problem_factor_confirm_button.place(x=80, y=115)

        self.problem_object = problem_directory[self.problem_var.get()]

        count_factors_problem = 1
        for factor_type in self.problem_object().specifications:
            print("size of dictionary", len(self.problem_object().specifications[factor_type]))
            print("first", factor_type)
            print("second", self.problem_object().specifications[factor_type].get("description"))
            print("third", self.problem_object().specifications[factor_type].get("datatype"))    
            print("fourth", self.problem_object().specifications[factor_type].get("default"))   

            self.dictionary_size_problem = len(self.problem_object().specifications[factor_type])

            if self.problem_object().specifications[factor_type].get("datatype") != bool:

                print("yes?")
                self.int_float_description_problem = tk.Label(master=self.factor_tab_one_problem,
                                                    text = str(self.problem_object().specifications[factor_type].get("description")),
                                                    font = "Calibri 11 bold")

                self.int_float_var_problem = tk.StringVar(self.factor_tab_one_problem)
                self.int_float_entry_problem = ttk.Entry(master=self.factor_tab_one_problem, textvariable = self.int_float_var_problem, justify = tk.LEFT)
                self.int_float_entry_problem.insert(index=tk.END, string=str(self.problem_object().specifications[factor_type].get("default")))

                self.int_float_description_problem.grid(row=count_factors_problem, column=0, sticky='nsew')
                self.int_float_entry_problem.grid(row=count_factors_problem, column=1, sticky='nsew')

                self.problem_factors_list.append(self.int_float_var_problem)

                count_factors_problem += 1


            if self.problem_object().specifications[factor_type].get("datatype") == bool:

                print("yes!")
                self.boolean_description_problem = tk.Label(master=self.factor_tab_one_problem,
                                                    text = str(self.problem_object().specifications[factor_type].get("description")),
                                                    font = "Calibri 11 bold")

                self.boolean_list_problem = ["True", "False"]
                self.boolean_var_problem = tk.StringVar(self.factor_tab_one_problem)

                self.boolean_menu_problem = ttk.OptionMenu(self.factor_tab_one_problem, self.boolean_var_problem, str(self.problem_object().specifications[factor_type].get("default")), *self.boolean_list)

                # self.boolean_datatype_problem = tk.Label(master=self.factor_tab_one,
                #                                     text = str(self.problem_object().specifications[factor_type].get("datatype")),
                #                                     font = "Calibri 11 bold")

                self.boolean_description_problem.grid(row=count_factors_problem, column=0, sticky='nsew')
                self.boolean_menu_problem.grid(row=count_factors_problem, column=1, sticky='nsew')
                # self.boolean_datatype_problem.grid(row=count_factors, column=2, sticky='nsew')

                self.problem_factors_list.append(self.boolean_var_problem)

                count_factors_problem += 1

        count_factors_problem += 1

        self.save_label_problem = tk.Label(master=self.factor_tab_one_problem,
                                            text = "Save Problem As",
                                            font = "Calibri 11 bold")

        self.save_var_problem = tk.StringVar(self.factor_tab_one_problem)
        self.save_entry_problem = ttk.Entry(master=self.factor_tab_one_problem, textvariable = self.save_var_problem, justify = tk.LEFT)
        self.save_entry_problem.insert(index=tk.END, string=self.problem_var.get())

        self.save_label_problem.grid(row=count_factors_problem, column=0, sticky='nsew')
        self.save_entry_problem.grid(row=count_factors_problem, column=1, sticky='nsew')

        self.problem_factors_list.append(self.save_var_problem)

        print(self.problem_factors_list)
        self.factor_label_frame_problem.place(x=400, y=70, height=150, width=475)

        # From Problems to Oracles

        self.oracle_factors_list = []
        problem = str(self.problem_var.get())
        self.oracle = problem.split("-")
        self.oracle = self.oracle[0]
        self.oracle_object = oracle_directory[self.oracle]

        self.factor_label_frame_oracle = ttk.Labelframe(master=self.master, text="Oracle Factors")

        self.factor_canvas_oracle = tk.Canvas(master=self.factor_label_frame_oracle, borderwidth=0)

        self.factor_frame_oracle = ttk.Frame(master=self.factor_canvas_oracle)
        self.vert_scroll_bar_factor_oracle = Scrollbar(self.factor_label_frame_oracle, orient="vertical", command=self.factor_canvas_oracle.yview)
        self.factor_canvas_oracle.configure(yscrollcommand=self.vert_scroll_bar_factor_oracle.set)

        self.horiz_scroll_bar_factor_oracle = Scrollbar(self.factor_label_frame_oracle, orient="horizontal", command=self.factor_canvas_oracle.xview)
        self.factor_canvas_oracle.configure(xscrollcommand=self.horiz_scroll_bar_factor_oracle.set)

        self.vert_scroll_bar_factor_oracle.pack(side="right", fill="y")
        self.horiz_scroll_bar_factor_oracle.pack(side="bottom", fill="x")

        self.factor_canvas_oracle.pack(side="left", fill="both", expand=True)
        self.factor_canvas_oracle.create_window((0,0), window=self.factor_frame_oracle, anchor="nw",
                                  tags="self.factor_frame_oracle")
        
        self.factor_frame_oracle.bind("<Configure>", self.onFrameConfigure_factor_oracle)

        self.factor_notebook_oracle = ttk.Notebook(master=self.factor_frame_oracle)
        self.factor_notebook_oracle.pack(fill="both")

        self.factor_tab_one_oracle = tk.Frame(master=self.factor_notebook_oracle)

        self.factor_notebook_oracle.add(self.factor_tab_one_oracle, text=str(self.oracle + " Factors"))

        self.factor_tab_one_oracle.grid_rowconfigure(0)

        self.factor_heading_list_oracle = ["Description", "Input"]

        for heading in self.factor_heading_list_oracle:
            self.factor_tab_one_oracle.grid_columnconfigure(self.factor_heading_list_oracle.index(heading))
            label_oracle = tk.Label(master=self.factor_tab_one_oracle, text=heading, font="Calibri 14 bold")
            label_oracle.grid(row=0, column=self.factor_heading_list_oracle.index(heading), padx=5, pady=3)

        self.oracle_factor_confirm_button = ttk.Button(master=self.master, # window button is used in
                    # aesthetic of button and specific formatting options
                    text = "Confirm Oracle Factors",
                    command = self.test_function)

        self.oracle_factor_confirm_button.place(x=220, y=115)

        count_factors_oracle = 1
        for factor_type in self.oracle_object().specifications:
            print("size of dictionary", len(self.oracle_object().specifications[factor_type]))
            print("first", factor_type)
            print("second", self.oracle_object().specifications[factor_type].get("description"))
            print("third", self.oracle_object().specifications[factor_type].get("datatype"))    
            print("fourth", self.oracle_object().specifications[factor_type].get("default"))   

            self.dictionary_size_oracle = len(self.oracle_object().specifications[factor_type])

            if self.oracle_object().specifications[factor_type].get("datatype") != bool:

                print("yes?")
                self.int_float_description_oracle = tk.Label(master=self.factor_tab_one_oracle,
                                                    text = str(self.oracle_object().specifications[factor_type].get("description")),
                                                    font = "Calibri 11 bold")

                self.int_float_var_oracle = tk.StringVar(self.factor_tab_one_oracle)
                self.int_float_entry_oracle = ttk.Entry(master=self.factor_tab_one_oracle, textvariable = self.int_float_var_oracle, justify = tk.LEFT, width = "50")
                self.int_float_entry_oracle.insert(index=tk.END, string=str(self.oracle_object().specifications[factor_type].get("default")))

                self.int_float_description_oracle.grid(row=count_factors_oracle, column=0, sticky='nsew')
                self.int_float_entry_oracle.grid(row=count_factors_oracle, column=1, sticky='nsew')

                self.oracle_factors_list.append(self.int_float_var_oracle)

                count_factors_oracle += 1


            if self.oracle_object().specifications[factor_type].get("datatype") == bool:

                print("yes!")
                self.boolean_description_oracle = tk.Label(master=self.factor_tab_one_oracle,
                                                    text = str(self.oracle_object().specifications[factor_type].get("description")),
                                                    font = "Calibri 11 bold")

                self.boolean_list_oracle = ["True", "False"]
                self.boolean_var_oracle = tk.StringVar(self.factor_tab_one_oracle)

                self.boolean_menu_oracle = ttk.OptionMenu(self.factor_tab_one_oracle, self.boolean_var_oracle, str(self.oracle_object().specifications[factor_type].get("default")), *self.boolean_list)

                # self.boolean_datatype_oracle = tk.Label(master=self.factor_tab_one,
                #                                     text = str(self.oracle_object().specifications[factor_type].get("datatype")),
                #                                     font = "Calibri 11 bold")

                self.boolean_description_oracle.grid(row=count_factors_oracle, column=0, sticky='nsew')
                self.boolean_menu_oracle.grid(row=count_factors_oracle, column=1, sticky='nsew')
                # self.boolean_datatype_oracle.grid(row=count_factors, column=2, sticky='nsew')

                self.oracle_factors_list.append(self.boolean_var_oracle)

                count_factors_oracle += 1

        print(self.oracle_factors_list)
        self.factor_label_frame_oracle.place(x=900, y=70, height=300, width=600)

    def show_solver_factors(self, *args):
        print("Got the solver: ", self.solver_var.get())

        self.solver_factors_list = []

        self.factor_label_frame_solver = ttk.Labelframe(master=self.master, text="Solver Factors")

        self.factor_canvas_solver = tk.Canvas(master=self.factor_label_frame_solver, borderwidth=0)

        self.factor_frame_solver = ttk.Frame(master=self.factor_canvas_solver)
        self.vert_scroll_bar_factor_solver = Scrollbar(self.factor_label_frame_solver, orient="vertical", command=self.factor_canvas_solver.yview)
        self.factor_canvas_solver.configure(yscrollcommand=self.vert_scroll_bar_factor_solver.set)

        self.horiz_scroll_bar_factor_solver = Scrollbar(self.factor_label_frame_solver, orient="horizontal", command=self.factor_canvas_solver.xview)
        self.factor_canvas_solver.configure(xscrollcommand=self.horiz_scroll_bar_factor_solver.set)

        self.vert_scroll_bar_factor_solver.pack(side="right", fill="y")
        self.horiz_scroll_bar_factor_solver.pack(side="bottom", fill="x")

        self.factor_canvas_solver.pack(side="left", fill="both", expand=True)
        self.factor_canvas_solver.create_window((0,0), window=self.factor_frame_solver, anchor="nw",
                                  tags="self.factor_frame_solver")
        
        self.factor_frame_solver.bind("<Configure>", self.onFrameConfigure_factor_solver)

        self.factor_notebook_solver = ttk.Notebook(master=self.factor_frame_solver)
        self.factor_notebook_solver.pack(fill="both")

        self.factor_tab_one_solver = tk.Frame(master=self.factor_notebook_solver)

        self.factor_notebook_solver.add(self.factor_tab_one_solver, text=str(self.solver_var.get()) + " Factors")

        self.factor_tab_one_solver.grid_rowconfigure(0)

        self.factor_heading_list_solver = ["Description", "Input"]

        for heading in self.factor_heading_list_solver:
            self.factor_tab_one_solver.grid_columnconfigure(self.factor_heading_list_solver.index(heading))
            label = tk.Label(master=self.factor_tab_one_solver, text=heading, font="Calibri 14 bold")
            label.grid(row=0, column=self.factor_heading_list_solver.index(heading), padx=5, pady=3)

        self.solver_factor_confirm_button = ttk.Button(master=self.master, # window button is used in
                    # aesthetic of button and specific formatting options
                    text = "Confirm Solver Factors",
                    command = self.test_function)

        self.solver_factor_confirm_button.place(x=220, y=195)

        self.solver_object = solver_directory[self.solver_var.get()]

        count_factors_solver = 1
        for factor_type in self.solver_object().specifications:
            print("size of dictionary", len(self.solver_object().specifications[factor_type]))
            print("first", factor_type)
            print("second", self.solver_object().specifications[factor_type].get("description"))
            print("third", self.solver_object().specifications[factor_type].get("datatype"))    
            print("fourth", self.solver_object().specifications[factor_type].get("default"))   

            self.dictionary_size = len(self.solver_object().specifications[factor_type])

            if self.solver_object().specifications[factor_type].get("datatype") != bool:

                self.int_float_description = tk.Label(master=self.factor_tab_one_solver,
                                                    text = str(self.solver_object().specifications[factor_type].get("description")),
                                                    font = "Calibri 11 bold")

                self.int_float_var = tk.StringVar(self.factor_tab_one_solver)
                self.int_float_entry = ttk.Entry(master=self.factor_tab_one_solver, textvariable = self.int_float_var, justify = tk.LEFT)
                self.int_float_entry.insert(index=tk.END, string=str(self.solver_object().specifications[factor_type].get("default")))

                # self.int_float_datatype = tk.Label(master=self.factor_tab_one,
                #                                     text = str(self.solver_object().specifications[factor_type].get("datatype")),
                #                                     font = "Calibri 11 bold")

                self.int_float_description.grid(row=count_factors_solver, column=0, sticky='nsew')
                self.int_float_entry.grid(row=count_factors_solver, column=1, sticky='nsew')
                # self.int_float_datatype.grid(row=count_factors_solver, column=2, sticky='nsew')
                
                self.solver_factors_list.append(self.int_float_var)
                count_factors_solver += 1


            if self.solver_object().specifications[factor_type].get("datatype") == bool:

                self.boolean_description = tk.Label(master=self.factor_tab_one_solver,
                                                    text = str(self.solver_object().specifications[factor_type].get("description")),
                                                    font = "Calibri 11 bold")

                self.boolean_list = ["True", "False"]
                self.boolean_var = tk.StringVar(self.factor_tab_one_solver)

                self.boolean_menu = ttk.OptionMenu(self.factor_tab_one_solver, self.boolean_var, str(self.solver_object().specifications[factor_type].get("default")), *self.boolean_list)

                # self.boolean_datatype = tk.Label(master=self.factor_tab_one,
                #                                     text = str(self.solver_object().specifications[factor_type].get("datatype")),
                #                                     font = "Calibri 11 bold")

                self.boolean_description.grid(row=count_factors_solver, column=0, sticky='nsew')
                self.boolean_menu.grid(row=count_factors_solver, column=1, sticky='nsew')
                # self.boolean_datatype.grid(row=count_factors_solver, column=2, sticky='nsew')

                self.solver_factors_list.append(self.boolean_var)

                count_factors_solver += 1

        count_factors_solver += 1

        self.save_label_solver = tk.Label(master=self.factor_tab_one_solver,
                                            text = "Save Solver As",
                                            font = "Calibri 11 bold")

        self.save_var_solver = tk.StringVar(self.factor_tab_one_solver)
        self.save_entry_solver = ttk.Entry(master=self.factor_tab_one_solver, textvariable = self.save_var_solver, justify = tk.LEFT)
        self.save_entry_solver.insert(index=tk.END, string=self.solver_var.get())

        self.save_label_solver.grid(row=count_factors_solver, column=0, sticky='nsew')
        self.save_entry_solver.grid(row=count_factors_solver, column=1, sticky='nsew')

        self.solver_factors_list.append(self.save_var_solver)

        print(self.solver_factors_list)
        self.factor_label_frame_solver.place(x=400, y=220, height=150, width=475)

    def run_single_function(self):

        if self.problem_var.get() in problem_directory and self.solver_var.get() in solver_directory and self.macro_entry.get().isnumeric() != False:
            # creates blank list to store selections
            self.selected = []
            # grabs problem_var (whatever is selected our of OptionMenu)
            self.selected.append(self.problem_var.get())
            # grabs solver_var (" ")
            self.selected.append(self.solver_var.get())
            # grabs macro_entry
            self.selected.append(int(self.macro_entry.get()))

            # resets problem_var to default value
            self.problem_var.set("Problem")
            # resets solver_var to default value
            self.solver_var.set("Solver")

            # macro_entry is a positive integer
            if int(self.macro_entry.get()) != 0:
                # resets current entry from index 0 to length of entry
                self.macro_entry.delete(0, len(self.macro_entry.get()))
                # resets macro_entry textbox
                self.macro_entry.insert(index=tk.END, string="10")

                # complete experiment with given arguments
                self.macro_reps = self.selected[2]
                self.solver_name = self.selected[1]
                self.problem_name = self.selected[0]

                self.my_experiment = Experiment(self.solver_name, self.problem_name)
                self.experiment_object_list.append(self.my_experiment)
                self.my_experiment.run(n_macroreps=self.macro_reps)

                # calls postprocessing window
                self.newWindow = tk.Toplevel(self.master)
                self.newWindow.title("Post Processing Page")
                self.app = Post_Processing_Window(self.newWindow, self.my_experiment, self.selected[0], self.selected[1], self.selected[2])

                # prints selected (list) in console/terminal
                print("it works", self.selected)

                return self.selected

            else:
                # reset macro_entry to "10"
                self.macro_entry.delete(0, len(self.macro_entry.get()))
                # resets macro_entry textbox
                self.macro_entry.insert(index=tk.END, string="10")

                message = "Please enter a postivie (non zero) integer for the number of Macro Replications, example: 10"
                tk.messagebox.showerror(title="Error Window", message=message)

        # problem selected, but solver NOT selected
        elif self.problem_var.get() in problem_directory and self.solver_var.get() not in solver_directory:
            message = "You have not selected a Solver!"
            tk.messagebox.showerror(title="Error Window", message=message)   

        # problem NOT selected, but solver selected
        elif self.problem_var.get() not in problem_directory and self.solver_var.get() in solver_directory:
            message = "You have not selected a Problem!"
            tk.messagebox.showerror(title="Error Window", message=message)
        
        # macro_entry not numeric or negative
        elif self.macro_entry.get().isnumeric() == False:
            # reset macro_entry to "10"
            self.macro_entry.delete(0, len(self.macro_entry.get()))
            # resets macro_entry textbox
            self.macro_entry.insert(index=tk.END, string="10")

            message = "Please enter a positive (non zero) integer for the number of Macro Replications, example: 10"
            tk.messagebox.showerror(title="Error Window", message=message)

        # neither problem nor solver selected
        else:
            # reset problem_var
            self.problem_var.set("Problem")
            # reset solver_var
            self.solver_var.set("Solver")

            # reset macro_entry to "10"
            self.macro_entry.delete(0, len(self.macro_entry.get()))
            # resets macro_entry textbox
            self.macro_entry.insert(index=tk.END, string="10")

            message = "You have not selected all required fields, check for '*' near input boxes."
            tk.messagebox.showerror(title="Error Window", message=message)

    def crossdesign_function(self):
        self.crossdesign_solvers_and_problems = []
        self.crossdesign_experiments = []

        for solver in solver_directory:
            for problem in problem_directory:
                temp_pairing = [solver, problem]

                self.crossdesign_solvers_and_problems.append(temp_pairing)

        for pairing in self.crossdesign_solvers_and_problems:
            solver_object = pairing[0]
            problem_object = pairing[1]

            experiment = Experiment(solver_object, problem_object)

            self.crossdesign_experiments.append(experiment)
        
        print(self.crossdesign_experiments)

    def clearRow_function(self):
        self.row = self.viewEdit_button_added["text"]
        print(self.viewEdit_button_added["text"])
        self.row = self.row.split(". ")
        self.row = int(self.row[1])
        self.index_list = self.row - 1
        
        print("row=",self.row)
        print("index=",self.index_list)
        print(self.experiment_master_list[self.index_list])
        print(self.widget_list[self.index_list])
        print(self.experiment_object_list[self.index_list])

    def clear_queue(self):

        for widget in self.widget_list:
             widget.grid_remove()

        self.experiment_master_list.clear()
        self.experiment_object_list.clear()
        self.widget_list.clear()

    def add_function(self):
        
        if self.problem_var.get() in problem_directory and self.solver_var.get() in solver_directory and self.macro_entry.get().isnumeric() != False:
            # creates blank list to store selections
            self.selected = []
            # grabs problem_var (whatever is selected our of OptionMenu)
            self.selected.append(self.problem_var.get())
            # grabs solver_var (" ")
            self.selected.append(self.solver_var.get())
            # grabs macro_entry
            self.selected.append(int(self.macro_entry.get()))

            self.macro_reps = self.selected[2]
            self.solver_name = self.selected[1]
            self.problem_name = self.selected[0]

            self.my_experiment = Experiment(self.solver_name, self.problem_name)
            self.experiment_object_list.append(self.my_experiment)

            # resets problem_var to default value
            self.problem_var.set("Problem")
            # resets solver_var to default value
            self.solver_var.set("Solver")

            # macro_entry is a positive integer
            if int(self.macro_entry.get()) != 0:
                # resets current entry from index 0 to length of entry
                self.macro_entry.delete(0, len(self.macro_entry.get()))
                # resets macro_entry textbox
                self.macro_entry.insert(index=tk.END, string="10")

                # complete experiment with given arguments
                self.macro_reps = self.selected[2]
                self.solver_name = self.selected[1]
                self.problem_name = self.selected[0]

                self.experiment_master_list.append(self.selected)

                self.rows = 5
                count = 1
                for i in self.experiment_master_list:

                    self.problem_added = tk.Label(master=self.tab_one,
                                                   text=i[0],
                                                   font = "Calibri 10",
                                                   justify="center")
                    self.problem_added.grid(row=count, column=0, sticky='nsew', padx=5, pady=3)

                    self.solver_added = tk.Label(master=self.tab_one,
                                                   text=i[1],
                                                   font = "Calibri 10",
                                                   justify="center")
                    self.solver_added.grid(row=count, column=1, sticky='nsew', padx=5, pady=3)

                    self.macros_added = tk.Label(master=self.tab_one,
                                                   text=i[2],
                                                   font = "Calibri 10",
                                                   justify="center")
                    self.macros_added.grid(row=count, column=2, sticky='nsew', padx=5, pady=3)

                    self.run_button_added = ttk.Button(master=self.tab_one,
                                                      text="Run Exp. " + str(count),
                                                      command=self.test_function)
                    self.run_button_added.grid(row=count, column=3, sticky='nsew', padx=5, pady=3)

                    self.viewEdit_button_added = ttk.Button(master=self.tab_one,
                                                      text="View / Edit Exp. " + str(count),
                                                      command=self.test_function)
                    self.viewEdit_button_added.grid(row=count, column=4, sticky='nsew', padx=5, pady=3)

                    self.clear_button_added = ttk.Button(master=self.tab_one,
                                                      text="Clear Exp. " + str(count),
                                                      command=self.clearRow_function)
                    self.clear_button_added.grid(row=count, column=5, sticky='nsew', padx=5, pady=3)

                    self.widget_row = [self.problem_added, self.solver_added, self.macros_added, self.run_button_added, self.viewEdit_button_added, self.clear_button_added]
                    self.widget_list.append(self.widget_row)

                    count += 1

                print(self.experiment_master_list)
                print(self.widget_list)
                print(self.experiment_object_list)

            else:
                # reset macro_entry to "10"
                self.macro_entry.delete(0, len(self.macro_entry.get()))
                # resets macro_entry textbox
                self.macro_entry.insert(index=tk.END, string="10")

                message = "Please enter a postivie (non zero) integer for the number of Macro Replications, example: 10"
                tk.messagebox.showerror(title="Error Window", message=message)

            # prints selected (list) in console/terminal
            #print("it works", self.selected)

            return self.experiment_master_list

        # problem selected, but solver NOT selected
        elif self.problem_var.get() in problem_directory and self.solver_var.get() not in solver_directory:
            message = "You have not selected a Solver!"
            tk.messagebox.showerror(title="Error Window", message=message)
        
        # problem NOT selected, but solver selected
        elif self.problem_var.get() not in problem_directory and self.solver_var.get() in solver_directory:
            message = "You have not selected a Problem!"
            tk.messagebox.showerror(title="Error Window", message=message)
        
        # macro_entry not numeric or negative
        elif self.macro_entry.get().isnumeric() == False:
            # reset macro_entry to "10"
            self.macro_entry.delete(0, len(self.macro_entry.get()))
            # resets macro_entry textbox
            self.macro_entry.insert(index=tk.END, string="10")

            message = "Please enter a positive (non zero) integer for the number of Macro Replications, example: 10"
            tk.messagebox.showerror(title="Error Window", message=message)

        # neither problem nor solver selected
        else:
            # reset problem_var
            self.problem_var.set("Problem")
            # reset solver_var
            self.solver_var.set("Solver")

            # reset macro_entry to "10"
            self.macro_entry.delete(0, len(self.macro_entry.get()))
            # resets macro_entry textbox
            self.macro_entry.insert(index=tk.END, string="10")

            message = "You have not selected all required fields, check for '*' near input boxes."
            tk.messagebox.showerror(title="Error Window", message=message)

    def onFrameConfigure_queue(self, event):
        self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))

    def onFrameConfigure_factor_problem(self, event):
        self.factor_canvas_problem.configure(scrollregion=self.factor_canvas_problem.bbox("all"))

    def onFrameConfigure_factor_solver(self, event):
        self.factor_canvas_solver.configure(scrollregion=self.factor_canvas_solver.bbox("all"))

    def onFrameConfigure_factor_oracle(self, event):
        self.factor_canvas_oracle.configure(scrollregion=self.factor_canvas_oracle.bbox("all"))

    def test_function(self, *args):
        print("test function connected")

class Post_Processing_Window():
    def __init__(self, master, myexperiment, problem, solver, macro_reps):

        self.master = master
        self.problem = problem
        self.solver = solver
        self.macro_reps = macro_reps
        self.my_experiment = myexperiment

        self.frame = tk.Frame(self.master)

        self.n_postreps_label = ttk.Label(master = self.master,
                                    text = "Number of postreplications to take at each recommended solution:*",
                                    font = "Calibri 11 bold",
                                    wraplength = "300")

        self.n_postreps_var = tk.StringVar(self.master)
        self.n_postreps_entry = ttk.Entry(master=self.master, textvariable = self.n_postreps_var, justify = tk.LEFT)
        self.n_postreps_entry.insert(index=tk.END, string="100")

        self.n_postreps_init_opt_label = ttk.Label(master = self.master,
                                text = "Number of postreplications to take at initial x\u2070 and optimal x\u002A:*",
                                font = "Calibri 11 bold",
                                wraplength = "300")

        self.n_postreps_init_opt_var = tk.StringVar(self.master)
        self.n_postreps_init_opt_entry = ttk.Entry(master=self.master, textvariable = self.n_postreps_init_opt_var, justify = tk.LEFT)
        self.n_postreps_init_opt_entry.insert(index=tk.END, string="200")

        self.crn_across_budget_label = ttk.Label(master=self.master,
                                    text = "Use CRN for post-replications at solutions recommended at different times?*",
                                    font = "Calibri 11 bold",
                                    wraplength = "300")

        self.crn_across_budget_list = ["True", "False"]
        # stays the same, has to change into a special type of variable via tkinter function
        self.crn_across_budget_var = tk.StringVar(self.master)
        # sets the default OptionMenu selection
        # self.crn_across_budget_var.set("True")
        # creates drop down menu, for tkinter, it is called "OptionMenu"
        self.crn_across_budget_menu = ttk.OptionMenu(self.master, self.crn_across_budget_var, "Options", *self.crn_across_budget_list)

        self.crn_across_macroreps_label = ttk.Label(master=self.master,
                                        text = "Use CRN for post-replications at solutions recommended on different macroreplications?*",
                                        font = "Calibri 11 bold",
                                        wraplength = "300")

        self.crn_across_macroreps_list = ["True", "False"]
        # stays the same, has to change into a special type of variable via tkinter function
        self.crn_across_macroreps_var = tk.StringVar(self.master)
        # sets the default OptionMenu selection
        # self.crn_across_macroreps_var.set("False")
        # creates drop down menu, for tkinter, it is called "OptionMenu"
        self.crn_across_macroreps_menu = ttk.OptionMenu(self.master, self.crn_across_macroreps_var, "Options", *self.crn_across_macroreps_list)

        self.post_processing_run_label = ttk.Label(master=self.master, # window label is used for
                        text = "When ready, press the 'Run' button below:",
                        font = "Calibri 11 bold")

        self.post_processing_run_button = ttk.Button(master=self.master, # window button is used in
                        # aesthetic of button and specific formatting options
                        text = "Run", 
                        width = 15, # width of button
                        command = self.post_processing_run_function) # if command=function(), it will only work once, so cannot call function, only specify which one, activated by left mouse click

        self.n_postreps_label.pack()
        self.n_postreps_entry.pack()
        self.n_postreps_init_opt_label.pack()
        self.n_postreps_init_opt_entry.pack()
        self.crn_across_budget_label.pack()
        self.crn_across_budget_menu.pack()
        self.crn_across_macroreps_label.pack()
        self.crn_across_macroreps_menu.pack()
        self.post_processing_run_label.pack()
        self.post_processing_run_button.pack()

        self.frame.pack()

    def post_processing_run_function(self):
        self.experiment_list = [self.problem, self.solver, self.macro_reps]

        if self.n_postreps_entry.get().isnumeric() != False and self.n_postreps_init_opt_entry.get().isnumeric() != False and self.crn_across_budget_var.get() in self.crn_across_budget_list and self.crn_across_macroreps_var.get() in self.crn_across_macroreps_list:
            self.experiment_list.append(int(self.n_postreps_entry.get()))
            self.experiment_list.append(int(self.n_postreps_init_opt_entry.get()))

            # actually adding a boolean value to the list instead of a string
            if self.crn_across_budget_var.get()=="True":
                self.experiment_list.append(True)
            else:
                self.experiment_list.append(False)

            if self.crn_across_macroreps_var.get()=="True":
                self.experiment_list.append(True)
            else:
                self.experiment_list.append(False)
                        
            # reset n_postreps_entry
            self.n_postreps_entry.delete(0, len(self.n_postreps_entry.get()))
            self.n_postreps_entry.insert(index=tk.END, string="100")

            # reset n_postreps_init_opt_entry
            self.n_postreps_init_opt_entry.delete(0, len(self.n_postreps_init_opt_entry.get()))
            self.n_postreps_init_opt_entry.insert(index=tk.END, string="200")

            # reset crn_across_budget_bar
            self.crn_across_budget_var.set("True")

            # reset crn_across_macroreps_var 
            self.crn_across_macroreps_var.set("False")

            self.n_postreps = self.experiment_list[3] # int
            self.n_postreps_init_opt = self.experiment_list[4] # int
            self.crn_across_budget = self.experiment_list[5] # boolean
            self.crn_across_macroreps = self.experiment_list[6] # boolean

            self.my_experiment.post_replicate(n_postreps=self.n_postreps, n_postreps_init_opt=self.n_postreps_init_opt, crn_across_budget=self.crn_across_budget, crn_across_macroreps=self.crn_across_macroreps)
            print("post-replicate ran successfully")

            print(self.experiment_list)
            return self.experiment_list

        elif self.n_postreps_entry.get().isnumeric() == False:
            message = "Please enter a valid value for the number of post replications to take at each recommended solution."
            tk.messagebox.showerror(title="Error Window", message=message)

            self.n_postreps_entry.delete(0, len(self.n_postreps_entry.get()))
            self.n_postreps_entry.insert(index=tk.END, string="100")

        elif self.n_postreps_init_opt_entry.get().isnumeric() == False:
            message = "Please enter a valid value for the number of post repliactions at the initial x\u2070 and optimal x\u002A."
            tk.messagebox.showerror(title="Error Window", message=message)

            self.n_postreps_init_opt_entry.delete(0, len(self.n_postreps_init_opt_entry.get()))
            self.n_postreps_init_opt_entry.insert(index=tk.END, string="200")

        elif self.crn_across_macroreps_var.get() not in self.crn_across_macroreps_list:
            message = "Please answer the following question: 'Use CRN for post-replications at solutions recommended at different times?' with True or False."
            tk.messagebox.showerror(title="Error Window", message=message)

            self.crn_across_budget_var.set("----")

        elif self.crn_across_budget_var.get() not in self.crn_across_budget_list:
            message = "Please answer the following question: 'Use CRN for post-replications at solutions recommended on different macroreplications?' with True or False."
            tk.messagebox.showerror(title="Error Window", message=message)

            self.crn_across_macroreps_var.set("----")

        else:
            message = "You have not selected all required fields, check for '*' near input boxes."
            tk.messagebox.showerror(title="Error Window", message=message)

            self.n_postreps_init_opt_entry.delete(0, len(self.n_postreps_init_opt_entry.get()))
            self.n_postreps_init_opt_entry.insert(index=tk.END, string="6")

            self.crn_across_budget_var.set("True")

            self.crn_across_macroreps_var.set("False")

# def create_error(str):
#     # Will be completely replaced soon (see this url: https://docs.python.org/3/library/tkinter.messagebox.html)

#     # initialize error window
#     errorWindow = tk.Tk()

#     errorLabel = ttk.Label(master = errorWindow,
#                         # aesthetics of window
#                         text = str,
#                         foreground= "red",
#                         font = "Calibri 11 bold",
#                         wraplength = "600")
#     # not used below, but since there is not grid, must use here
#     errorLabel.pack()

#     # title of window
#     errorWindow.title("Error Window")
#     # starting size of window
#     errorWindow.geometry("700x100")
#     # required
#     errorWindow.mainloop()

def main(): 
    root = tk.Tk()
    root.title("SimOpt Application")
    root.geometry("1500x1000")
    root.pack_propagate(False)

    app = Experiment_Window(root)
    root.mainloop()

if __name__ == '__main__':
    main()




