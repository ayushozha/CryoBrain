module cryo_brain_decoder #(
    parameter int SYNDROME_WIDTH = 8,
    parameter int CORRECTION_WIDTH = 4,
    parameter int CONFIDENCE_WIDTH = 8
) (
    input  logic clk,
    input  logic rst_n,
    input  logic syndromes_valid,
    input  logic [SYNDROME_WIDTH-1:0] syndromes,
    output logic corrections_valid,
    output logic [CORRECTION_WIDTH-1:0] corrections,
    output logic [CONFIDENCE_WIDTH-1:0] confidence
);
    assign corrections = '0;
    assign corrections_valid = 1'b0;
    assign confidence = '0;
endmodule