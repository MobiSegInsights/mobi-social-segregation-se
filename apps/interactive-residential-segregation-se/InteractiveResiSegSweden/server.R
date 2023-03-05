#
# This is the server logic of a Shiny web application. You can run the
# application by clicking 'Run App' above.
#
# Find out more about building applications with Shiny here:
#
#    http://shiny.rstudio.com/
#

library(shiny)
library(mapdeck)
library(sf)
library(dplyr)
library(geojsonsf)

options(scipen = 0)
# Define server logic required to draw a histogram
function(input, output, session) {

    zones.resi <- geojson_sf("data/residential_income_segregation.geojson")
    
    output$selected_aspect <- renderText({ 
        if (input$aspect == 'evenness_income'){out <- "Net income: the sum of all taxable and tax-free income of a person minus tax and 
            other negative transfers (eg., repaid student loan). There are four quantile groups."}
        if (input$aspect == 'Foreign background') {out <- "Persons with a foreign background are defined as persons who were born abroad, 
        or born in Denmark with two foreign-born parents."}
        if (input$aspect == 'Lowest income group') {out <- "Share of lowest income."}
        out
    })
    
    
    output$segPlot <- renderMapdeck({
        key <- "pk.eyJ1IjoieXVhbmxpYW8iLCJhIjoiY2xkMGl6bGw1MWRqODNycDdiMmdoMzR1eSJ9.cW2c9yeQZG27b8Z37EUeVg"
        mapdeck(token = key, location = c(11.974116, 57.690063)
                , zoom = 14
                , style = mapdeck_style("street")
            )
            
    })
    
    ## use an observer to add and remove layers
    observeEvent(input$execute, {
            mapdeck_update(map_id = "segPlot") %>%
            clear_polygon(layer_id = "seg") %>%
            add_polygon(
                data = zones.resi
                , layer_id = 'seg'
                , fill_colour = input$aspect
                , legend = TRUE
                , legend_options = list(digits = 4)
                , fill_opacity = 200
                , update_view = F
            )
    })

}
