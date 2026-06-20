// Agent-facing starter RTL (intentionally minimal — improve for reward).
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
    logic [CORRECTION_WIDTH-1:0] corr_q;
    logic valid_q;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            corr_q <= '0;
            valid_q <= 1'b0;
        end else if (syndromes_valid) begin
            // Buggy starter: bitwise OR instead of XOR (passes the visible smoke
            // vector by coincidence — fix to XOR for real decode quality).
            corr_q <= syndromes[3:0] | syndromes[7:4];
            valid_q <= 1'b1;
        end else begin
            valid_q <= 1'b0;
        end
    end

    assign corrections = corr_q;
    assign corrections_valid = valid_q;
    assign confidence = 8'd32;
endmodule