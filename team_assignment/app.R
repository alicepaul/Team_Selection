library(shiny)
library(ompr)
source('optimize_teams.R')

# Cost constants ----
PREF_COSTS <- c(1000,100,5,1,0)

# UI for app ----
ui <- fluidPage(
  
  # App title and description ----
  titlePanel("Let's create some project teams!"),
  
  h3("About this app:"),
  p("Find potential project teams that reflect project preferences and conflicts. The app searches for the most diverse set of solutions within max optimality gap of optimal. Costs for assigning a person to a project are preset based on the preference level but can also be inputted by the user. Additional constraints guaranteeing or preventing certain assignments can also be added."),
  
  h3("File Formats:"),
  p("Project csv file must include a row for each project and a column labelled project_name with each project name. If included, columns max_staff and min_staff will be used for limits on team sizes. All other columns ignored for now."),
  p("Personnel csv file must include a row for each person and a column labelled name with each person's name. It also must include a column labelled with each project name containing each person's score from 1 to 5 for that project (1 = strong dislike, 5 = strong preference). If included, the column labelled conflicts is assumed to have a list of names of people someone cannot work with (e.x. \"Alice,John\"). All other columns are ignored for now."),
  
  tags$hr(),
  
  # Sidebar layout with input and output definitions ----
  sidebarLayout(
    
    # Sidebar panel for inputs ----
    sidebarPanel(
  
    # Input: Select a project file ----
    fileInput("file_proj", "Choose Project CSV File",
              accept = c("text/csv",
                         "text/comma-separated-values,text/plain",
                         ".csv")),
    
    # Input: Select a personnel file ----
    fileInput("file_pers", "Choose Personnel CSV File",
              accept = c("text/csv",
                         "text/comma-separated-values,text/plain",
                         ".csv")),
        
    # Input: Max number of diverse solutions ----
    numericInput("num_div", "Max # of Solutions to Find", 3),
    
    # Input: Optimality gap for diverse solutions ----
    numericInput("gap_div", "Max Optimality Gap (%)", 0),
    
    # Horizontal line ----
    tags$hr(),
    
    # Input: User inputted costs ----
    checkboxInput("own_costs","Set own costs"),
    conditionalPanel(
      condition = "input.own_costs == true",
      numericInput("cost5", "Cost Preference 5", 0),
      numericInput("cost4", "Cost Preference 4", 1),
      numericInput("cost3", "Cost Preference 3", 5),
      numericInput("cost2", "Cost Preference 2", 100),
      numericInput("cost1", "Cost Preference 1", 1000)
    ),

    # Horizontal line ----
    tags$hr(),
    
    # Input: Reoptimize solutions ----
    actionButton("go", "Optimize!")
    ),
    
    # Main panel for displaying outputs ----
    mainPanel(
      
      textOutput(outputId = "status"),
      
      # Tabs for output (teams, comparisons, constraints, project data, personnel data) ----
      tabsetPanel(type = "tabs",
                  tabPanel("Teams",
                           selectInput("solnid","Solution",1:1,selected=1),
                           uiOutput("solns")
                           ),
                  tabPanel("Compare",
                           fluidRow(
                             column(4,selectInput("diff1","Solution",1:1,selected=1)),
                             column(4,selectInput("diff2","Solution",1:1,selected=1)),
                             column(4,selectInput("typeCompare","Show",c("Similarities","Differences")))
                           ),
  
                           uiOutput("compare")
                  ),
                  tabPanel("Constraints",
                           h5("Constraints"),
                           actionButton('addConstraint', 'Add Constraint'), 
                           tags$hr(),
                           tags$div(id = 'placeholderAddRemConstraint'),
                           tags$div(id = 'placeholderConstraint'),
                           actionButton('removeAll', 'Remove All')
                  ),
                  tabPanel("Project File",dataTableOutput(outputId = "projects")),
                  tabPanel("Personnel File",dataTableOutput(outputId = "personnel")))
      
    )
  )
)

# Server ----
server <- function(input, output, session) {
  
  # Reactive ui for adding/removing constraints ----
  makeReactiveBinding("aggregConstraintObserver")
  aggregConstraintObserver <- list()
  currentIds <- c()
  
  # Add constraint event
  observeEvent(input$addConstraint, {
    req(input$file_proj)
    req(input$file_pers)
    df_proj <- read.csv(input$file_proj$datapath)
    df_pers <- read.csv(input$file_pers$datapath)
    add <- input$addConstraint
    constraintId <- paste0('Constraint_', add)
    persConstraintId <- paste0('Pers_Constriant_', add)
    typeConstraintId <- paste0('Type_Constraint_', add)
    projConstraintId <- paste0('Proj_Constraint_', add)
    removeConstraintId <- paste0('Remove_Constraint_', add)
    currentIds <<- c(constraintId, currentIds)
    print(currentIds)
    insertUI(
      selector = '#placeholderConstraint',
      ui = tags$div(id = constraintId,
                    fluidRow(
                      column(4,selectInput(persConstraintId, label = "Person", choices = as.list(df_pers$"name"))),
                      column(2,selectInput(typeConstraintId, label = "", choices = c("on","not on"))),
                      column(4,selectInput(projConstraintId, label = "Project", choices = as.list(df_proj$"project_name"))),
                      column(1,actionButton(removeConstraintId, label = "X", style = "float: right;"))
                    )
      )
    )
    
    # Update constraint values
    observeEvent(input[[persConstraintId]], {
      aggregConstraintObserver[[constraintId]]$pers <<- input[[persConstraintId]]
    })
    observeEvent(input[[typeConstraintId]], {
      aggregConstraintObserver[[constraintId]]$type <<- input[[typeConstraintId]]
    })
    observeEvent(input[[projConstraintId]], {
      aggregConstraintObserver[[constraintId]]$proj <<- input[[projConstraintId]]
    })
    
    # Remove individual constraint
    observeEvent(input[[removeConstraintId]], {
      currentIds <<- currentIds[!currentIds == removeConstraintId]
      removeUI(selector = paste0('#', constraintId))
      aggregConstraintObserver[[constraintId]] <<- NULL
    })
  })
  
  # Remove all constraints
  observeEvent(input$removeAll,{
    print(currentIds)
    for (constraintId in currentIds){
      removeUI(selector = paste0('#',constraintId))
      aggregConstraintObserver[[constraintId]] <<- NULL
    } 
    currentIds <<- c()
  })
  
  
  # Optimization for teams ----
  runOpt <- eventReactive(input$go,{
    req(input$file_proj)
    req(input$file_pers)
    pcosts <- PREF_COSTS
    if (input$own_costs == TRUE){
      pcosts <- c(input$cost1,input$cost2,input$cost3,input$cost4,input$cost5)
    }
    result <- try(optimizeTeams(input$file_proj$datapath, input$file_pers$datapath,input$num_div,input$gap_div,aggregConstraintObserver,pcosts))
    if(class(result)=="try-error"){
      result <- list("status"="err")
      return(result)
    }
    if (result$status == 'opt'){
      updateSelectInput(session, "solnid",label = "Solution",choices = 1:length(result$values),selected = 1)
      updateSelectInput(session, "diff1",label = "Solution",choices = 1:length(result$values),selected = 1)
      updateSelectInput(session, "diff2",label = "Solution",choices = 1:length(result$values),selected = 1)
    }
    return(result)
  })
  
  # Status of system ----
  output$status <- renderText({
    result <- runOpt()
    print(result$status)
    if (result$status=="opt"){
      paste("Status optimized at ",Sys.time())
    }
    else if (result$status=="infeasible"){
      paste("Infeasible problem - check format of files and constraints ",Sys.time())
    }
    else{
      paste("Error - check format of files ",Sys.time())
    }
  })
  
  # File displays ----
  output$projects <- renderDataTable({
    req(input$file_proj)
    read.csv(input$file_proj$datapath)
  })
  
  output$personnel <- renderDataTable({
    req(input$file_pers)
    read.csv(input$file_pers$datapath)
  })
  
  
  # Solution displays ----
  output$solns <- renderUI({
    result <- runOpt()
    output$teamcost <- renderText({paste("Cost: ",result$values[[as.numeric(input$solnid)]])})
    output$teamdata <- renderTable({result$teams[[as.numeric(input$solnid)]]})
    output$dfteam <- downloadHandler(
      filename = function() {
        paste("soltuion-", input$solnid, ".csv", sep="")
      },
      content = function(file) {
        write.csv(result$teams[[as.numeric(input$solnid)]], file)
      }
    )
    tagList(
      textOutput("teamcost"),
      tableOutput("teamdata"),
      downloadLink("dfteam","Download assignment")
    )
  })
  
  
  # Comparison of solutions display ----
  output$compare <- renderUI({
    result <- runOpt()
    value1 <- result$values[[as.numeric(input$diff1)]]
    value2 <- result$values[[as.numeric(input$diff2)]]
    output$diffcost1 <- renderText(paste("Cost of",as.numeric(input$diff1),": ",value1,", Cost of",as.numeric(input$diff2),": ",value2))
    
    df1 <- result$teams[[as.numeric(input$diff1)]]
    df2 <- result$teams[[as.numeric(input$diff2)]]
    df <- merge(df1,df2,by="name")
    if (input$typeCompare == "Similarities"){
      df <- df[df$'project.x' == df$'project.y',]
    }
    else{
      df <- df[df$'project.x'!= df$'project.y',]      
    }
    colnames(df)[colnames(df)=="project.x"] <- paste("project",as.numeric(input$diff1))
    colnames(df)[colnames(df)=="project.y"] <- paste("project",as.numeric(input$diff2))
    colnames(df)[colnames(df)=="preference.x"] <- paste("preference",as.numeric(input$diff1))
    colnames(df)[colnames(df)=="preference.y"] <- paste("preference",as.numeric(input$diff1))
    output$difftable <- renderDataTable(df)
    
    tagList(
      textOutput("diffcost1"),
      textOutput("diffcost2"),
      dataTableOutput("difftable")
    )
  })
  
}

# Create Shiny app ----
shinyApp(ui = ui, server = server)